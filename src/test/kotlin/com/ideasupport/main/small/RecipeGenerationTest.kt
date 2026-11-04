package com.ideasupport.main.small

import com.ideasupport.core.dto.app.recipe.*
import com.ideasupport.infra.ai.AiClient
import com.ideasupport.lib.common.component.ContentPolicyComponent
import com.ideasupport.lib.common.exception.ServerErrorException
import com.ideasupport.main.app.recipe.RecipeGenerationComponent
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.DynamicTest.dynamicTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestFactory
import org.mockito.Mockito.*

class RecipeGenerationTest {
	private val valid =
		GeneratedRecipeDto("food", true, "안전한 만드는 법", listOf(IngredientOutDto("감자", "2개")), listOf(RecipeStepOutDto(1, "준비", "재료를 씻습니다")))

	private fun generate(result: GeneratedRecipeDto): GeneratedRecipeDto {
		val ai = mock(AiClient::class.java)
		`when`(ai.generateRecipe("분야", "제목", "내용")).thenReturn(result)
		return RecipeGenerationComponent(ai, ContentPolicyComponent()).generate("분야", "제목", "내용")
	}

	@Test fun `올바른 음식 레시피는 그대로 반환된다`() {
		assertEquals(valid, generate(valid))
	}

	@Test fun `음식이 아닌 실행 계획은 잘못된 제공자 출력으로 거부된다`() {
		assertEquals(1108, assertThrows(ServerErrorException::class.java) { generate(valid.copy(kind = "plan")) }.errorCode)
	}

	@Test fun `불가능 결과는 이유 설명과 빈 배열을 요구한다`() {
		assertFalse(generate(valid.copy(feasible = false, ingredients = emptyList(), steps = emptyList())).feasible)
	}

	@TestFactory fun `형식이 깨진 제공자 출력은 거부된다`() =
		listOf(
			"알 수 없는 유형" to valid.copy(kind = "other"),
			"요약이 비어 있음" to valid.copy(summary = " "),
			"요약이 너무 김" to valid.copy(summary = "가".repeat(2001)),
			"재료가 너무 많음" to valid.copy(ingredients = List(41) { valid.ingredients.first() }),
			"재료 이름이 비어 있음" to valid.copy(ingredients = listOf(IngredientOutDto("", "1개"))),
			"양이 비어 있음" to valid.copy(ingredients = listOf(IngredientOutDto("감자", ""))),
			"양이 너무 김" to valid.copy(ingredients = listOf(IngredientOutDto("감자", "가".repeat(201)))),
			"가능한데 단계가 없음" to valid.copy(steps = emptyList()),
			"단계 순서가 틀림" to valid.copy(steps = listOf(RecipeStepOutDto(2, "준비", "설명"))),
			"단계 제목이 비어 있음" to valid.copy(steps = listOf(RecipeStepOutDto(1, "", "설명"))),
			"단계 설명이 너무 김" to valid.copy(steps = listOf(RecipeStepOutDto(1, "준비", "가".repeat(2001)))),
			"단계가 너무 많음" to valid.copy(steps = (1..31).map { RecipeStepOutDto(it, "단계", "설명") }),
			"불가능인데 단계가 있음" to valid.copy(feasible = false),
		).map {
				(name, result) ->
			dynamicTest(name) { assertEquals(1108, assertThrows(ServerErrorException::class.java) { generate(result) }.errorCode) }
		}

	@TestFactory fun `제공자의 모든 문자열 필드에 콘텐츠 정책이 적용된다`() =
		listOf(
			"요약" to valid.copy(summary = "폭탄 제조"),
			"재료 이름" to valid.copy(ingredients = listOf(IngredientOutDto("폭탄 제조", "1개"))),
			"재료 양" to valid.copy(ingredients = listOf(IngredientOutDto("감자", "폭탄 제조"))),
			"단계 제목" to valid.copy(steps = listOf(RecipeStepOutDto(1, "폭탄 제조", "설명"))),
			"단계 설명" to valid.copy(steps = listOf(RecipeStepOutDto(1, "준비", "폭탄 제조"))),
		).map {
				(name, result) ->
			dynamicTest(name) { assertEquals(1106, assertThrows(ServerErrorException::class.java) { generate(result) }.errorCode) }
		}
}
