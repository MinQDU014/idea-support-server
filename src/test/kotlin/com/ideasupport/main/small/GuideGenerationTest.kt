package com.ideasupport.main.small

import com.ideasupport.core.dto.app.guide.*
import com.ideasupport.core.dto.app.recipe.*
import com.ideasupport.infra.ai.AiClient
import com.ideasupport.lib.common.component.ContentPolicyComponent
import com.ideasupport.lib.common.exception.ServerErrorException
import com.ideasupport.main.app.guide.*
import com.ideasupport.main.app.recipe.RecipeGenerationComponent
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.DynamicTest.dynamicTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestFactory
import org.mockito.kotlin.*

class GuideGenerationTest {
	private val ai = mock<AiClient>()
	private val policy = ContentPolicyComponent()
	private val component = GuideGenerationComponent(ai, RecipeGenerationComponent(ai, policy), policy)
	private val valid =
		GeneratedGuideDto(
			"software",
			true,
			"아이디어의 최소 구현 계획",
			listOf(GuideRequirementDto("개발 환경", "필요한 도구")),
			listOf(GuideStepDto(1, "핵심 기능", "작은 동작부터 구현합니다.")),
		)

	private fun generate(value: GeneratedGuideDto): GeneratedGuideDto {
		whenever(ai.generateGuide("분야", "제목", "내용", "software")).thenReturn(value)
		return component.generate(GuideType.SOFTWARE, "분야", "제목", "내용")
	}

	@TestFactory fun `음식이 아닌 분야는 각자의 가이드를 만든다`() =
		listOf(GuideType.SOFTWARE, GuideType.CONTEST, GuideType.GENERAL).map { type ->
			dynamicTest(type.value) {
				whenever(ai.generateGuide("분야", "제목", "내용", type.value)).thenReturn(valid.copy(kind = type.value))
				assertEquals(type.value, component.generate(type, "분야", "제목", "내용").kind)
			}
		}

	@Test fun `음식은 요리 어댑터를 사용한다`() {
		whenever(
			ai.generateRecipe("음식", "제목", "내용"),
		).thenReturn(GeneratedRecipeDto("food", true, "요약", emptyList(), listOf(RecipeStepOutDto(1, "조리", "조리합니다"))))
		assertEquals("food", component.generate(GuideType.FOOD, "음식", "제목", "내용").kind)
		verify(ai, never()).generateGuide(any(), any(), any(), any())
	}

	@Test fun `불가능한 가이드는 빈 배열을 요구한다`() {
		assertFalse(generate(valid.copy(feasible = false, requirements = emptyList(), steps = emptyList())).feasible)
	}

	@TestFactory fun `잘못되었거나 맞지 않는 제공자 내용은 거부된다`() =
		listOf(
			"유형이 다름" to valid.copy(kind = "food"), "요약이 비어 있음" to valid.copy(summary = ""), "요약이 너무 김" to valid.copy(summary = "가".repeat(2001)),
			"준비물이 너무 많음" to valid.copy(requirements = List(41) { valid.requirements.first() }),
			"이름이 비어 있음" to valid.copy(requirements = listOf(GuideRequirementDto("", "도구"))), "이름이 너무 김" to valid.copy(requirements = listOf(GuideRequirementDto("가".repeat(201), "도구"))),
			"설명이 비어 있음" to valid.copy(requirements = listOf(GuideRequirementDto("개발", ""))), "설명이 너무 김" to valid.copy(requirements = listOf(GuideRequirementDto("개발", "가".repeat(201)))),
			"단계가 없음" to valid.copy(steps = emptyList()), "단계가 너무 많음" to valid.copy(steps = (1..31).map { GuideStepDto(it, "단계", "설명") }),
			"단계 순서가 틀림" to valid.copy(steps = listOf(GuideStepDto(2, "단계", "설명"))), "단계 제목이 비어 있음" to valid.copy(steps = listOf(GuideStepDto(1, "", "설명"))),
			"단계 제목이 너무 김" to valid.copy(steps = listOf(GuideStepDto(1, "가".repeat(201), "설명"))), "단계 설명이 비어 있음" to valid.copy(steps = listOf(GuideStepDto(1, "단계", ""))),
			"단계 설명이 너무 김" to valid.copy(steps = listOf(GuideStepDto(1, "단계", "가".repeat(2001)))), "불가능인데 단계가 있음" to valid.copy(feasible = false),
		).map {
				(name, value) ->
			dynamicTest(name) { assertEquals(1108, assertThrows(ServerErrorException::class.java) { generate(value) }.errorCode) }
		}

	@Test fun `위험한 안내는 거부된다`() {
		assertEquals(1106, assertThrows(ServerErrorException::class.java) { generate(valid.copy(summary = "폭탄 제조")) }.errorCode)
	}

	@Test fun `지원하지 않는 유형이 암묵적으로 요리 가이드가 될 수 없다`() {
		assertThrows(ServerErrorException::class.java) { GuideType.from("plan") }
	}
}
