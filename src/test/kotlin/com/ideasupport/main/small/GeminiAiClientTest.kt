package com.ideasupport.main.small

import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.ideasupport.infra.ai.GeminiAiClient
import com.ideasupport.infra.ai.GeminiHttpComponent
import com.ideasupport.lib.common.exception.ServerErrorException
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.DynamicTest.dynamicTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestFactory
import org.mockito.kotlin.any
import org.mockito.Mockito.*
import java.net.http.HttpResponse
import java.net.http.HttpTimeoutException
import java.io.IOException

class GeminiAiClientTest {
	@TestFactory fun `유형별 가이드는 실제 호출 없이 Gemini 전송 계층으로 해석된다`() =
		listOf("software", "contest", "general").map { kind ->
			dynamicTest(kind) {
				respond(
					body =
						envelope(
							"""{"kind":"$kind","feasible":true,"summary":"분야별 가이드","requirements":[{"name":"준비","detail":"자료"}],"steps":[{"order":1,"title":"검증","description":"작게 시작합니다"}]}""",
						),
				)
				val result = client().generateGuide("카테고리", "아이디어 제목", "구체적인 아이디어", kind)
				assertEquals(kind, result.kind)
				assertEquals("자료", result.requirements.first().detail)
			}
		}

	@Test fun `지원하지 않는 가이드 유형은 제공자를 호출하지 않는다`() {
		assertThrows(ServerErrorException::class.java) { client().generateGuide("분야", "제목", "설명", "unknown") }
		verifyNoInteractions(transport)
	}

	private val mapper = jacksonObjectMapper()
	private val transport = mock(GeminiHttpComponent::class.java)

	private fun client(
		key: String = "test-only-key",
		model: String = "test-model",
	) = GeminiAiClient(
		mapper,
		key,
		model,
		5,
		20,
		15,
		1,
		transport,
	)

	private fun respond(
		status: Int = 200,
		body: String,
	) {
		@Suppress("UNCHECKED_CAST")
		val response = mock(HttpResponse::class.java) as HttpResponse<String>
		`when`(response.statusCode()).thenReturn(status)
		`when`(response.body()).thenReturn(body)
		`when`(transport.send(any())).thenReturn(response)
	}

	private fun envelope(text: String) =
		mapper.writeValueAsString(
			mapOf("candidates" to listOf(mapOf("finishReason" to "STOP", "content" to mapOf("parts" to listOf(mapOf("text" to text)))))),
		)

	private fun generate(api: GeminiAiClient = client()) = api.generateIdea("음식", listOf("감자", "치즈", "캠핑"), "간편", null)

	@Test fun `올바른 구조의 응답은 해석된다`() {
		respond(body = envelope("""{"title":"제목","content":"설명"}"""))
		assertEquals("제목", generate().title)
	}

	@TestFactory fun `제공자 HTTP 오류는 고정된 도메인 오류로 변환된다`() =
		listOf(429 to 1107, 401 to 1109, 500 to 1109).map { (status, error) ->
			dynamicTest("HTTP $status") {
				respond(status, "private upstream error")
				assertEquals(error, assertThrows(ServerErrorException::class.java) { generate() }.errorCode)
			}
		}

	@TestFactory fun `잘못된 응답 껍데기는 거부된다`() =
		listOf(
			"후보가 없음" to "{}",
			"정상 종료가 아님" to """{"candidates":[{"finishReason":"MAX_TOKENS"}]}""",
			"내용이 비어 있음" to envelope(""),
			"내용이 너무 큼" to envelope("a".repeat(50001)),
			"안쪽 JSON이 잘못됨" to envelope("not-json"),
			"필수 필드가 없음" to envelope("{}"),
		).map { (name, body) ->
			dynamicTest(name) {
				respond(body = body)
				assertEquals(1108, assertThrows(ServerErrorException::class.java) { generate() }.errorCode)
			}
		}

	@Test fun `시간 초과는 504 도메인 오류이며 재시도를 위해 허가를 반납한다`() {
		`when`(transport.send(any())).thenAnswer { throw HttpTimeoutException("timeout") }
		val api = client()
		assertEquals(1110, assertThrows(ServerErrorException::class.java) { generate(api) }.errorCode)
		respond(body = envelope("""{"title":"회복","content":"성공"}"""))
		assertEquals("회복", generate(api).title)
	}

	@Test fun `네트워크 실패는 제공자 세부 정보를 숨긴다`() {
		`when`(transport.send(any())).thenAnswer { throw IOException("private upstream data") }
		val error = assertThrows(ServerErrorException::class.java) { generate() }
		assertEquals(1109, error.errorCode)
		assertFalse(error.message!!.contains("private"))
	}

	@Test fun `인증 정보가 없거나 모델이 잘못되면 제공자에 연락하지 않는다`() {
		assertThrows(ServerErrorException::class.java) { generate(client(key = "")) }
		assertThrows(ServerErrorException::class.java) { generate(client(model = "../bad")) }
		verifyNoInteractions(transport)
	}

	@Test fun `생각 부분은 구조화된 출력에서 제외된다`() {
		respond(
			body = """{"candidates":[{"finishReason":"STOP","content":{"parts":[{"thought":true,"text":"hidden reasoning"},{"text":"{\"title\":\"제목\",\"content\":\"설명\"}"}]}}]}""",
		)
		assertEquals("제목", generate().title)
	}

	@Test fun `단어 매칭은 문자열 배열을 요구한다`() {
		respond(body = envelope("""{"wordIds":[123]}"""))
		assertEquals(1108, assertThrows(ServerErrorException::class.java) { client().selectWords("주제", emptyList()) }.errorCode)
	}

	@Test fun `단어 매칭은 이후 후보 검증을 위해 아이디를 반환한다`() {
		respond(body = envelope("""{"wordIds":["w1","w2"]}"""))
		assertEquals(listOf("w1", "w2"), client().selectWords("주제", emptyList()))
	}
}
