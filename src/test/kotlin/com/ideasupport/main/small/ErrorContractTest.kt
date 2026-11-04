package com.ideasupport.main.small

import com.ideasupport.lib.common.enum.INTERNAL_ERROR_CODE
import com.ideasupport.lib.common.exception.ServerErrorException
import com.ideasupport.lib.common.handler.GlobalServerErrorExceptionHandler
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test
import org.springframework.mock.web.MockHttpServletRequest

class ErrorContractTest {
	private val handler = GlobalServerErrorExceptionHandler()

	@Test fun `요청 제한 응답은 재시도 시간과 고정된 JSON 필드를 포함한다`() {
		val response = handler.domain(ServerErrorException(INTERNAL_ERROR_CODE.RATE_LIMITED, 42))
		assertEquals(429, response.statusCode.value())
		assertEquals("42", response.headers.getFirst("Retry-After"))
		assertEquals(1107, response.body!!.code)
		assertEquals("RATE_LIMITED", response.body!!.name)
	}

	@Test fun `간격이 없는 요청 제한은 60초를 쓴다`() {
		assertEquals("60", handler.domain(ServerErrorException(INTERNAL_ERROR_CODE.RATE_LIMITED)).headers.getFirst("Retry-After"))
	}

	@Test fun `입력 실패는 도메인 JSON과 함께 400이다`() {
		assertEquals(1100, handler.input(IllegalArgumentException()).body!!.code)
	}

	@Test fun `없는 자원은 404다`() {
		assertEquals(404, handler.missing().statusCode.value())
	}

	@Test fun `예상하지 못한 예외는 내부 메시지를 노출하지 않는다`() {
		val result = handler.unexpected(IllegalStateException("private-provider-key"), MockHttpServletRequest("POST", "/app/ideas"))
		assertEquals(500, result.statusCode.value())
		assertEquals(9997, result.body!!.code)
		assertFalse(result.body.toString().contains("private-provider-key"))
	}
}
