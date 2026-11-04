package com.ideasupport.main.small

import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.ideasupport.core.dto.app.idea.GeneratedIdeaDto
import com.ideasupport.infra.ai.AiClient
import com.ideasupport.lib.common.component.ContentPolicyComponent
import com.ideasupport.lib.common.exception.ServerErrorException
import com.ideasupport.main.app.idea.IdeaGenerationComponent
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.DynamicTest.dynamicTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestFactory
import org.mockito.Mockito.*

class IdeaGenerationTest {
	private val ai = mock(AiClient::class.java)
	private val component = IdeaGenerationComponent(ai, ContentPolicyComponent(), jacksonObjectMapper())
	private val words = listOf("감자", "캠핑", "치즈")

	@Test fun `캐시 키는 단어 순서를 무시하고 카테고리와 방향과 모델 버전은 구분한다`() {
		`when`(ai.cacheVersion).thenReturn("v1")
		val key = component.key("c", words, "간편")
		assertEquals(key, component.key("c", words.reversed(), "간편"))
		assertNotEquals(key, component.key("other", words, "간편"))
		assertNotEquals(key, component.key("c", words, "건강"))
		`when`(ai.cacheVersion).thenReturn("v2")
		assertNotEquals(key, component.key("c", words, "간편"))
	}

	@Test fun `올바른 아이디어는 변형 요청과 함께 그대로 전달된다`() {
		val expected = GeneratedIdeaDto("감자 캠핑 치즈", "세 단어를 활용한 요리")
		`when`(ai.generateIdea("음식", words, "간편", "variation")).thenReturn(expected)
		assertEquals(expected, component.generate("음식", words, "간편", "variation"))
	}

	@TestFactory fun `비어 있거나 너무 긴 출력은 거부된다`() =
		listOf(
			GeneratedIdeaDto("", "설명"),
			GeneratedIdeaDto("가".repeat(161), "설명"),
			GeneratedIdeaDto("제목", " "),
			GeneratedIdeaDto("제목", "가".repeat(10001)),
		).mapIndexed { index, result ->
			dynamicTest("잘못된 출력 $index") {
				`when`(ai.generateIdea("음식", words, "", null)).thenReturn(result)
				assertEquals(1108, assertThrows(ServerErrorException::class.java) { component.generate("음식", words, "", null) }.errorCode)
			}
		}

	@Test fun `위험한 입력은 제공자를 부르기 전에 거부된다`() {
		assertThrows(ServerErrorException::class.java) { component.generate("음식", words, "폭탄 제조", null) }
		verifyNoInteractions(ai)
	}

	@Test fun `위험한 제공자 출력은 거부된다`() {
		`when`(ai.generateIdea("음식", words, "", null)).thenReturn(GeneratedIdeaDto("폭탄 제조", "설명"))
		assertEquals(1106, assertThrows(ServerErrorException::class.java) { component.generate("음식", words, "", null) }.errorCode)
	}
}
