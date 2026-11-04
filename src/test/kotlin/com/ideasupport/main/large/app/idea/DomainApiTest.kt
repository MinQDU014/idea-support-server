package com.ideasupport.main.large.app.idea

import com.ideasupport.core.dto.app.recipe.*
import com.ideasupport.lib.common.enum.INTERNAL_ERROR_CODE
import com.ideasupport.lib.common.exception.ServerErrorException
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.DynamicTest.dynamicTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestFactory
import org.mockito.ArgumentMatchers.*
import org.mockito.Mockito.*
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*
import java.util.UUID

class DomainApiTest : MySqlApiTestSupport() {
	@Test fun `로컬 React 미리보기가 출력된 IPv4 주소 출처를 허용한다`() {
		val response =
			mvc.perform(
				options(
					"/app/user/sign-up",
				).header(
					"Origin",
					"http://127.0.0.1:5173",
				).header("Access-Control-Request-Method", "POST").header("Access-Control-Request-Headers", "content-type"),
			).andReturn().response
		assertEquals(200, response.status)
		assertEquals("http://127.0.0.1:5173", response.getHeader("Access-Control-Allow-Origin"))
	}

	@Test fun `허용 목록에 없는 출처는 계속 거부된다`() {
		assertEquals(
			403,
			mvc.perform(
				options("/app/ideas").header("Origin", "https://unlisted.example").header("Access-Control-Request-Method", "POST"),
			).andReturn().response.status,
		)
	}

	@TestFactory fun `모든 업무 엔드포인트는 액세스 인증을 요구한다`() =
		listOf(
			Triple("GET", "/app/categories", null), Triple("POST", "/app/categories/preview", mapOf("name" to "요리")),
			Triple("POST", "/app/categories", mapOf("name" to "요리")), Triple("POST", "/app/words/draw", mapOf("categoryId" to "c")),
			Triple("POST", "/app/ideas", mapOf("categoryId" to "c", "wordIds" to listOf("a", "b", "c"))),
			Triple(
				"GET",
				"/app/ideas/missing",
				null,
			),
			Triple("POST", "/app/ideas/missing/recombine", null), Triple("POST", "/app/ideas/missing/recipe", null),
			Triple("POST", "/app/shares", mapOf("ideaId" to "i")), Triple("POST", "/app/posts", mapOf("ideaId" to "i")),
			Triple("GET", "/app/posts", null), Triple("PUT", "/app/posts/missing/reaction", mapOf("kind" to "like")),
		).map { (method, path, body) -> dynamicTest("$method $path") { request(method, path, body, expected = 401) } }

	@TestFactory fun `잘못된 사용자 입력은 AI를 시작하지 않고 400 JSON을 반환한다`() =
		listOf(
			"빈 카테고리 이름" to ("/app/categories" to mapOf("name" to " ")),
			"너무 긴 카테고리 이름" to ("/app/categories/preview" to mapOf("name" to "가".repeat(51))),
			"카테고리 없이 단어 뽑기" to ("/app/words/draw" to emptyMap<String, Any>()),
			"단어 두 개" to ("/app/ideas" to mapOf("categoryId" to "c", "wordIds" to listOf("a", "b"))),
			"단어 네 개" to ("/app/ideas" to mapOf("categoryId" to "c", "wordIds" to listOf("a", "b", "c", "d"))),
			"너무 긴 방향" to ("/app/ideas" to mapOf("categoryId" to "c", "wordIds" to listOf("a", "b", "c"), "direction" to "가".repeat(201))),
			"빈 공유 아이디어" to ("/app/shares" to mapOf("ideaId" to "")),
			"아이디어 없는 게시글" to ("/app/posts" to emptyMap<String, Any>()),
		).map { (name, input) ->
			dynamicTest(name) {
				val (token, _) = member()
				clearInvocations(ai)
				assertEquals(1100, request("POST", input.first, input.second, token, 400)["code"].asInt())
				verifyNoInteractions(ai)
			}
		}

	@Test fun `깨진 JSON은 공통 입력 오류를 받는다`() {
		val (token, _) = member()
		val response =
			mvc.perform(
				post("/app/ideas").header("Authorization", "Bearer $token").contentType("application/json").content("{bad-json"),
			).andReturn().response
		assertEquals(400, response.status)
		assertEquals(1100, mapper.readTree(response.contentAsByteArray)["code"].asInt())
	}

	@TestFactory fun `피드는 정렬 기준과 개수 제한과 커서 형식을 검증한다`() =
		listOf("sort=unknown", "limit=0", "limit=51", "limit=text", "cursor=not-json").map { query ->
			dynamicTest(query) {
				val (token, _) = member()
				assertEquals(1100, request("GET", "/app/posts?$query", token = token, expected = 400)["code"].asInt())
			}
		}

	@Test fun `깨끗한 데이터베이스에서는 시드 개수와 빈 피드를 예측할 수 있다`() {
		val (token, _) = member()
		val items = request("GET", "/app/categories", token = token)["items"]
		assertEquals(listOf(148, 149, 152), items.map { it["wordCount"].asInt() }.sorted())
		assertEquals(441, jdbc.queryForObject("SELECT COUNT(*) FROM words", Int::class.java))
		val feed = request("GET", "/app/posts", token = token)
		assertTrue(feed["items"].isEmpty)
		assertTrue(feed["nextCursor"].isNull)
	}

	@Test fun `회원가입은 중복 아이디를 막고 비밀번호를 해시로 저장한다`() {
		val id = "user-${UUID.randomUUID()}"
		val body = mapOf("id" to id, "pw" to "password", "email" to "student@example.com", "name" to "학생", "birth" to "2000-01-01")
		request("POST", "/app/user/sign-up", body)
		assertEquals(51, request("POST", "/app/user/sign-up", body, expected = 409)["code"].asInt())
		assertNotEquals("password", jdbc.queryForObject("SELECT pw FROM users WHERE id=?", String::class.java, id))
		assertEquals(6, request("POST", "/app/user/login", mapOf("id" to id, "pw" to "wrong"), expected = 400)["code"].asInt())
		request("POST", "/app/user/login", mapOf("id" to "no-user", "pw" to "wrong"), expected = 404)
	}

	@Test fun `액세스 토큰과 리프레시 토큰은 용도를 바꿔 쓸 수 없다`() {
		val (access, refresh) = member()
		request("POST", "/app/user/refresh-token", mapOf("refreshToken" to access), expected = 401)
		request("GET", "/app/user/profile", token = refresh, expected = 401)
		request("GET", "/app/categories", token = "$access-tampered", expected = 401)
		request("POST", "/app/user/refresh-token", mapOf("refreshToken" to refresh))
	}

	@Test fun `카테고리 미리보기는 저장하지 않으며 일치하는 단어가 부족하면 422를 반환한다`() {
		val (token, _) = member()
		val before = categories.count()
		val preview = request("POST", "/app/categories/preview", mapOf("name" to "캠핑 요리"), token)
		assertTrue(preview["canCreate"].asBoolean())
		assertEquals(before, categories.count())
		request("POST", "/app/categories", mapOf("name" to "무의미한xyz"), token, 422)
		assertEquals(before, categories.count())
	}

	@Test fun `고정 단어 세 개와 다른 카테고리의 아이디는 거부된다`() {
		val (token, _) = member()
		val body = input()
		request("POST", "/app/words/draw", mapOf("categoryId" to body["categoryId"], "lockedWordIds" to body["wordIds"]), token, 400)
		val other = categories.findAll().first { it.name == "프로그램 개발" }
		val foreign =
			words.findCategoryWords(other.id).first {
				it.id !in
					words.findCategoryWords(body["categoryId"].toString()).map {
							w ->
						w.id
					}
			}
		request("POST", "/app/words/draw", mapOf("categoryId" to body["categoryId"], "lockedWordIds" to listOf(foreign.id)), token, 400)
	}

	@TestFactory fun `없는 자원은 404를 반환한다`() =
		listOf(
			"GET" to "/app/ideas/missing",
			"POST" to "/app/ideas/missing/recombine",
			"POST" to "/app/ideas/missing/recipe",
			"PUT" to "/app/posts/missing/reaction",
		).map { (method, path) ->
			dynamicTest(path) {
				val (token, _) = member()
				request(method, path, if (method == "PUT") mapOf("kind" to "like") else null, token, 404)
			}
		}

	@Test fun `링크 전용 글은 피드에 나오지 않고 반응을 받을 수 없다`() {
		val (owner, _) = member()
		val (other, _) = member()
		val id = request("POST", "/app/ideas", input(), owner, 201)["idea"]["id"].asText()
		val link = request("POST", "/app/shares", mapOf("ideaId" to id), owner, 201)
		assertTrue(request("GET", "/app/posts", token = other)["items"].isEmpty)
		request("PUT", "/app/posts/${link["postId"].asText()}/reaction", mapOf("kind" to "like"), other, 404)
		assertFalse(request("POST", "/app/shares", mapOf("ideaId" to id), owner)["created"].asBoolean())
	}

	@Test fun `잘못된 반응은 400을 반환하고 반응이 없는 상태의 취소는 여러 번 해도 결과가 같다`() {
		val (owner, _) = member()
		val (other, _) = member()
		val id = request("POST", "/app/ideas", input(), owner, 201)["idea"]["id"].asText()
		val post = request("POST", "/app/posts", mapOf("ideaId" to id), owner, 201)["postId"].asText()
		request("PUT", "/app/posts/$post/reaction", mapOf("kind" to "wrong"), other, 400)
		repeat(2) { assertTrue(request("PUT", "/app/posts/$post/reaction", mapOf("kind" to null), other)["myReaction"].isNull) }
	}

	@Test fun `레시피 제공자 실패는 저장되지 않고 다음 호출에서 복구된다`() {
		val (token, _) = member()
		val id = request("POST", "/app/ideas", input(), token, 201)["idea"]["id"].asText()
		doThrow(ServerErrorException(INTERNAL_ERROR_CODE.AI_TIMEOUT)).`when`(ai).generateRecipe(anyString(), anyString(), anyString())
		request("POST", "/app/ideas/$id/recipe", token = token, expected = 504)
		assertEquals(0, jdbc.queryForObject("SELECT COUNT(*) FROM recipes", Int::class.java))
		doCallRealMethod().`when`(ai).generateRecipe(anyString(), anyString(), anyString())
		request("POST", "/app/ideas/$id/recipe", token = token, expected = 201)
		assertTrue(request("GET", "/app/ideas/$id", token = token)["idea"]["hasRecipe"].asBoolean())
	}

	@Test fun `만들 수 없는 레시피도 유효한 캐시 결과다`() {
		val (token, _) = member()
		val id = request("POST", "/app/ideas", input(), token, 201)["idea"]["id"].asText()
		doReturn(
			GeneratedRecipeDto("food", false, "현재 조건으로 조리할 수 없습니다", emptyList(), emptyList()),
		).`when`(ai).generateRecipe(anyString(), anyString(), anyString())
		assertFalse(request("POST", "/app/ideas/$id/recipe", token = token, expected = 201)["recipe"]["feasible"].asBoolean())
		assertTrue(request("POST", "/app/ideas/$id/recipe", token = token)["cached"].asBoolean())
	}

	@TestFactory fun `개발용 경로와 운영 시연 경로는 계속 막혀 있다`() =
		listOf("/app/dev/get-pw/test", "/common/ip/init", "/common/error", "/common/user-level-lock").map { path ->
			dynamicTest(path) {
				assertEquals(403, mvc.perform(get(path)).andReturn().response.status)
			}
		}
}
