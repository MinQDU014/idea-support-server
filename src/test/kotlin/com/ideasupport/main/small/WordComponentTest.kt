package com.ideasupport.main.small

import com.ideasupport.core.entity.WordEntity
import com.ideasupport.infra.repository.WordRepository
import com.ideasupport.lib.common.component.ContentPolicyComponent
import com.ideasupport.lib.common.exception.ServerErrorException
import com.ideasupport.main.app.word.WordComponent
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.DynamicTest.dynamicTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestFactory
import org.mockito.Mockito.*

class WordComponentTest {
	private val repository = mock(WordRepository::class.java)
	private val component = WordComponent(repository, ContentPolicyComponent())
	private val pool = (1..8).map { WordEntity(id = "w$it", text = "단어$it") }

	@Test fun `검증은 요청한 순서를 유지한다`() {
		`when`(repository.findCategoryWords("c")).thenReturn(pool)
		assertEquals(listOf("w3", "w1", "w2"), component.validate("c", listOf("w3", "w1", "w2"), 3).map { it.id })
	}

	@TestFactory fun `개수가 틀리거나 중복되거나 다른 풀의 아이디는 거부된다`() =
		listOf(listOf("w1"), listOf("w1", "w1", "w2"), listOf("w1", "w2", "foreign")).map { ids ->
			dynamicTest(ids.toString()) {
				`when`(repository.findCategoryWords("c")).thenReturn(pool)
				assertEquals(1100, assertThrows(ServerErrorException::class.java) { component.validate("c", ids, 3) }.errorCode)
			}
		}

	@Test fun `뽑기는 풀에서 서로 다른 단어 세 개를 반환한다`() {
		val result = component.draw(pool, emptyList(), emptyList())
		assertEquals(3, result.map { it.id }.distinct().size)
		assertTrue(result.all { it in pool })
	}

	@Test fun `고정한 단어는 유지되고 두 번 뽑히지 않는다`() {
		val result = component.draw(pool, pool.take(2), emptyList())
		assertEquals(pool.take(2), result.take(2))
		assertEquals(3, result.map { it.id }.distinct().size)
	}

	@Test fun `대안이 충분하면 다시 뽑기는 이전 단어를 제외한다`() {
		assertTrue(component.draw(pool, emptyList(), pool.take(3).map { it.id }).none { it in pool.take(3) })
	}

	@Test fun `풀이 작으면 자리를 잃는 대신 이전 단어를 다시 쓴다`() {
		assertEquals(3, component.draw(pool.take(3), emptyList(), pool.take(3).map { it.id }).size)
	}

	@Test fun `풀이 부족하면 도메인 오류를 반환한다`() {
		assertEquals(1104, assertThrows(ServerErrorException::class.java) { component.draw(pool.take(2), emptyList(), emptyList()) }.errorCode)
	}
}
