package com.ideasupport.main.small

import com.ideasupport.lib.common.component.ContentPolicyComponent
import com.ideasupport.lib.common.exception.ServerErrorException
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.DynamicTest.dynamicTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestFactory

class ContentPolicyTest {
	private val policy = ContentPolicyComponent()

	@Test fun `호환 문자와 공백은 정규화된다`() {
		assertEquals("ABC 건강 관리", policy.normalize("  ＡＢＣ\t건강\n관리  "))
	}

	@Test fun `이름 키는 대소문자와 공백과 호환 문자를 무시한다`() {
		assertEquals(policy.key("AI 건강 관리"), policy.key("ａｉ건강관리"))
	}

	@Test fun `해시는 항상 같은 UTF8 SHA256 값이다`() {
		assertEquals(64, policy.hash("감자").length)
		assertEquals(policy.hash("감자"), policy.hash("감자"))
		assertNotEquals(policy.hash("감자"), policy.hash("고구마"))
	}

	@Test fun `평범한 창작 내용은 허용된다`() {
		assertDoesNotThrow { policy.check("학생을 위한 건강한 요리 프로그램") }
	}

	@Test fun `잘못된 입력은 공개 도메인 오류로 변환된다`() {
		assertEquals(1100, assertThrows(ServerErrorException::class.java) { policy.requireInput(false) }.errorCode)
	}

	@TestFactory fun `정규화한 뒤 위험한 문구는 거부된다`() =
		listOf("폭탄제조", "자살  방법").map { value ->
			dynamicTest(value) { assertEquals(1106, assertThrows(ServerErrorException::class.java) { policy.check(value) }.errorCode) }
		}

	// 새 기능은 실패하는 테스트부터 쓴다(Red). 보이지 않는 문자로 위험 문구 검사를 피하는 구멍을 막는다.
	@Test fun `보이지 않는 문자는 정규화할 때 제거된다`() {
		assertEquals("건강관리", policy.normalize("건강\u200B관리"))
	}

	@TestFactory fun `보이지 않는 문자를 끼워 넣어도 위험한 문구는 거부된다`() =
		listOf("폭탄\u200B제조", "자살\u200D방법").map { value ->
			dynamicTest(value.replace(Regex("\\p{Cf}"), "(보이지 않는 문자)")) {
				assertEquals(1106, assertThrows(ServerErrorException::class.java) { policy.check(value) }.errorCode)
			}
		}
}
