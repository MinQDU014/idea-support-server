package com.ideasupport.main.small

import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.ideasupport.core.entity.*
import com.ideasupport.infra.ai.AiClient
import com.ideasupport.infra.repository.MatchCacheRepository
import com.ideasupport.lib.common.component.*
import com.ideasupport.lib.common.exception.ServerErrorException
import com.ideasupport.main.app.word.*
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.DynamicTest.dynamicTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestFactory
import org.mockito.kotlin.*
import java.time.Instant
import java.util.Optional

class WordMatchTest {
	private val ai = mock<AiClient>()
	private val repository = mock<MatchCacheRepository>()
	private val mapper = jacksonObjectMapper()
	private val cache = WordMatchCacheComponent(repository, mapper)
	private val component =
		WordMatchComponent(ai, ContentPolicyComponent(), cache, GenerationCoordinatorComponent(), RequestLimitComponent(100, 100, 100, 100))
	private val pool = (1..15).map { WordEntity(id = "w$it", text = "단어$it") }

	private fun provider() {
		whenever(ai.source).thenReturn("gemini")
		whenever(ai.cacheVersion).thenReturn("test-v1")
		whenever(repository.findById(any())).thenReturn(Optional.empty())
	}

	@Test fun `키워드 일치가 충분하면 AI를 아예 쓰지 않는다`() {
		provider()
		val tagged = pool.map { WordEntity(id = it.id, text = it.text, keywords = "캠핑 요리") }
		val result = component.match("캠핑", tagged, 10, 1)
		assertEquals("keyword", result.source)
		assertEquals(15, result.words.size)
		verify(ai, never()).selectWords(any(), any())
	}

	@Test fun `모의 모드는 일치하는 단어를 지어내지 않는다`() {
		whenever(ai.source).thenReturn("mock")
		assertTrue(component.match("unrelated", pool, 10, 1).words.isEmpty())
		verify(ai, never()).selectWords(any(), any())
	}

	@Test fun `올바른 제공자 아이디는 캐시되고 후보 풀에서 반환된다`() {
		provider()
		whenever(ai.selectWords(any(), any())).thenReturn(pool.take(10).map { it.id })
		val result = component.match("건강 관리", pool, 10, 1)
		assertEquals("ai", result.source)
		assertEquals(pool.take(10).map { it.id }.toSet(), result.words.map { it.id }.toSet())
		verify(repository).save(check<MatchCacheEntity> { assertEquals(10, mapper.readTree(it.result).size()) })
	}

	@TestFactory fun `중복되거나 후보 밖이거나 너무 많은 AI 선택은 캐시하지 않고 거부한다`() =
		listOf(listOf("w1", "w1"), listOf("foreign"), (1..41).map { "w$it" }).map { ids ->
			dynamicTest("잘못된 선택 개수 ${ids.size}") {
				provider()
				whenever(ai.selectWords(any(), any())).thenReturn(ids)
				assertEquals(1108, assertThrows(ServerErrorException::class.java) { component.match("건강 관리", pool, 10, 1) }.errorCode)
				verify(repository, never()).save(any())
			}
		}

	@Test fun `유효한 캐시는 제공자를 부르지 않고 아이디를 현재 단어로 되돌린다`() {
		provider()
		whenever(
			repository.findById(any()),
		).thenReturn(Optional.of(MatchCacheEntity(result = "[\"w1\",\"w2\"]", expiresAt = Instant.now().plusSeconds(60))))
		val result = component.match("건강 관리", pool, 3, 1)
		assertEquals("cache", result.source)
		assertEquals(pool.take(2), result.words)
		verify(ai, never()).selectWords(any(), any())
	}

	@Test fun `만료된 캐시는 무시한다`() {
		whenever(repository.findById("old")).thenReturn(Optional.of(MatchCacheEntity(expiresAt = Instant.now().minusSeconds(1))))
		assertNull(cache.get("old"))
	}

	@Test fun `후보 메타데이터가 바뀌면 캐시 키가 달라진다`() {
		provider()
		whenever(ai.selectWords(any(), any())).thenReturn(emptyList())
		component.match("건강", pool, 3, 1)
		component.match("건강", pool.map { WordEntity(id = it.id, text = "바뀐${it.text}") }, 3, 1)
		val saved = argumentCaptor<MatchCacheEntity>()
		verify(repository, times(2)).save(saved.capture())
		assertNotEquals(saved.allValues[0].cacheKey, saved.allValues[1].cacheKey)
	}
}
