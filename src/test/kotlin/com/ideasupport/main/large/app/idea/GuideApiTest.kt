package com.ideasupport.main.large.app.idea

import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.DynamicTest.dynamicTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestFactory
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get
import java.util.UUID

class GuideApiTest : MySqlApiTestSupport() {
	private val defaults =
		listOf(Triple("음식 개발", "food", "만드는 법"), Triple("프로그램 개발", "software", "구현 가이드"), Triple("공모전 주제선정", "contest", "공모전 기획안"))

	private fun createIdea(
		categoryId: String,
		token: String,
	): String =
		request(
			"POST",
			"/app/ideas",
			mapOf(
				"categoryId" to categoryId,
				"wordIds" to
					words.findCategoryWords(categoryId).take(3).map {
						it.id
					},
				"direction" to UUID.randomUUID().toString(),
			),
			token,
			201,
		)["idea"]["id"].asText()

	@TestFactory fun `기본 카테고리마다 알맞은 재사용 가이드를 생성한다`() =
		defaults.map { (name, kind, label) ->
			dynamicTest(name) {
				val (token, _) = member()
				val category = categories.findAll().first { it.name == name }
				val id = createIdea(category.id, token)
				val result = request("POST", "/app/ideas/$id/guide", token = token, expected = 201)
				assertEquals(kind, result["guide"]["kind"].asText())
				assertEquals(label, result["guide"]["label"].asText())
				assertTrue(result["guide"]["requirements"].size() > 0)
				assertTrue(result["guide"]["steps"].size() > 0)
				assertTrue(request("POST", "/app/ideas/$id/guide", token = token)["cached"].asBoolean())
				val output = request("GET", "/app/ideas/$id", token = token)["idea"]
				assertEquals(kind, output["guideType"].asText())
				assertTrue(output["hasGuide"].asBoolean())
				val share = request("POST", "/app/shares", mapOf("ideaId" to id), token, 201)
				val html = mvc.perform(get("/s/${share["shareCode"].asText()}")).andReturn().response
				assertEquals(200, html.status)
				assertTrue(html.getContentAsString(Charsets.UTF_8).contains("<h2>$label</h2>"))
			}
		}

	@TestFactory fun `사용자 카테고리는 명시한 가이드 유형을 저장한다`() =
		listOf("food", "software", "contest", "general").map { kind ->
			dynamicTest(kind) {
				val (token, _) = member()
				val custom =
					request(
						"POST",
						"/app/categories",
						mapOf("name" to "캠핑 요리 ${UUID.randomUUID()}", "guideType" to kind),
						token,
						201,
					)["category"]
				assertEquals(kind, custom["guideType"].asText())
				val id = createIdea(custom["id"].asText(), token)
				val result = request("POST", "/app/ideas/$id/guide", token = token, expected = 201)
				assertEquals(kind, result["guide"]["kind"].asText())
				val listed = request("GET", "/app/categories", token = token)["items"].first { it["id"].asText() == custom["id"].asText() }
				assertEquals(kind, listed["guideType"].asText())
			}
		}

	@Test fun `유형이 없는 사용자 카테고리는 실행 계획을 받는다`() {
		val (token, _) = member()
		val custom = request("POST", "/app/categories", mapOf("name" to "캠핑 요리 ${UUID.randomUUID()}"), token, 201)["category"]
		assertEquals("general", custom["guideType"].asText())
		assertEquals("실행 계획", custom["guideLabel"].asText())
	}

	@Test fun `알 수 없는 가이드 유형은 거부된다`() {
		val (token, _) = member()
		request("POST", "/app/categories", mapOf("name" to "캠핑 요리", "guideType" to "unknown"), token, 400)
	}

	@Test fun `예전 레시피 경로도 프로그램 가이드를 지원한다`() {
		val (token, _) = member()
		val category = categories.findAll().first { it.name == "프로그램 개발" }
		val id = createIdea(category.id, token)
		val result = request("POST", "/app/ideas/$id/recipe", token = token, expected = 201)
		assertEquals("software", result["recipe"]["kind"].asText())
		assertTrue(request("POST", "/app/ideas/$id/guide", token = token)["cached"].asBoolean())
	}
}
