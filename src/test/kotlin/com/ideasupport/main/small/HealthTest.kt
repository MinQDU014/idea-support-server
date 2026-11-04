package com.ideasupport.main.small

import com.ideasupport.infra.ai.AiClient
import com.ideasupport.main.common.health.HealthComponent
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test
import org.mockito.kotlin.*
import org.springframework.jdbc.core.JdbcTemplate

class HealthTest {
	private val jdbc = mock<JdbcTemplate>()
	private val ai = mock<AiClient>()
	private val component = HealthComponent(jdbc, ai)

	@Test fun `데이터베이스가 정상이고 시드가 완전하면 ok를 반환한다`() {
		whenever(jdbc.queryForObject(any<String>(), eq(Int::class.java))).thenReturn(1, 3)
		whenever(ai.source).thenReturn("mock")
		assertEquals("ok", component.status().status)
	}

	@Test fun `시드가 불완전하면 DB 장애로 보지 않고 준비 상태만 낮춘다`() {
		whenever(jdbc.queryForObject(any<String>(), eq(Int::class.java))).thenReturn(1, 2)
		whenever(ai.source).thenReturn("mock")
		val result = component.status()
		assertEquals("degraded", result.status)
		assertEquals("up", result.database)
		assertFalse(result.seedReady)
	}

	@Test fun `데이터베이스 장애는 스택 트레이스 대신 저하 상태를 반환한다`() {
		whenever(jdbc.queryForObject(any<String>(), eq(Int::class.java))).thenThrow(IllegalStateException("private database detail"))
		whenever(ai.source).thenReturn("gemini")
		val result = component.status()
		assertEquals("down", result.database)
		assertFalse(result.seedReady)
		assertEquals("gemini", result.aiMode)
	}
}
