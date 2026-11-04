package com.ideasupport.main.small
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Assertions.*
import com.ideasupport.lib.common.component.RequestLimitComponent
import com.ideasupport.lib.common.exception.ServerErrorException
import java.time.Clock
import java.time.Instant
import java.time.ZoneId
import java.time.ZoneOffset

class RequestLimitTest {
	// 시간이 흐르는 상황을 만들기 위한 가짜 시계. 실제로 기다리지 않고 now 값만 바꾼다.
	private class MutableClock(var now: Instant) : Clock() {
		override fun getZone(): ZoneId = ZoneOffset.UTC

		override fun withZone(zone: ZoneId): Clock = this

		override fun instant(): Instant = now
	}

	@Test fun `회원 한도를 넘으면 재시도 간격을 알려 준다`() {
		val limits = RequestLimitComponent(1, 1, 1, 1)
		limits.check("generation", 1)
		val error = assertThrows(ServerErrorException::class.java) { limits.check("generation", 1) }
		assertEquals(1107, error.errorCode)
		assertTrue(error.retryAfterSeconds!! in 1..60)
	}

	@Test fun `행동별 허용 횟수와 회원별 허용 횟수는 서로 독립이다`() {
		val limits = RequestLimitComponent(1, 1, 1, 1)
		limits.check("generation", 1)
		assertDoesNotThrow {
			limits.check("recipe", 1)
			limits.check("generation", 2)
		}
	}

	@Test fun `공유 IP는 합산 한도가 정해져 있다`() {
		val limits = RequestLimitComponent(1, 1, 1, 1)
		(1L..3L).forEach { limits.check("generation", it) }
		assertThrows(ServerErrorException::class.java) { limits.check("generation", 4) }
	}

	@Test fun `카테고리 생성은 하루 단위 재시도 간격을 쓴다`() {
		val limits = RequestLimitComponent(1, 1, 1, 1)
		limits.check("category", 1)
		val error = assertThrows(ServerErrorException::class.java) { limits.check("category", 1) }
		assertTrue(error.retryAfterSeconds!! in 86395..86400)
	}

	// Red: 시간이 지나면 한도가 다시 열려야 한다. 시계를 바꿔 끼울 수 없어서 처음에는 컴파일부터 실패한다.
	@Test fun `60초가 지나면 회원 한도가 다시 열린다`() {
		// 준비: 한도 1회, 시각을 마음대로 움직일 수 있는 시계
		val clock = MutableClock(Instant.parse("2026-11-04T00:00:00Z"))
		val limits = RequestLimitComponent(1, 1, 1, 1, clock)
		limits.check("generation", 1)
		assertThrows(ServerErrorException::class.java) { limits.check("generation", 1) }

		// 실행: 61초가 흐른다
		clock.now = clock.now.plusSeconds(61)

		// 검증: 같은 회원이 다시 요청할 수 있다
		assertDoesNotThrow { limits.check("generation", 1) }
	}

	@Test fun `60초가 지나기 전에는 한도가 계속 막혀 있다`() {
		val clock = MutableClock(Instant.parse("2026-11-04T00:00:00Z"))
		val limits = RequestLimitComponent(1, 1, 1, 1, clock)
		limits.check("generation", 1)

		clock.now = clock.now.plusSeconds(59)

		assertThrows(ServerErrorException::class.java) { limits.check("generation", 1) }
	}
}
