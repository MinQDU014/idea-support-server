package com.ideasupport.main.common.health

import com.ideasupport.lib.common.annotation.Api
import io.swagger.v3.oas.annotations.tags.Tag
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.RequestMethod
import org.springframework.web.bind.annotation.RestController

@Tag(name = "DeployDemo", description = "배포 버전 확인")
@RestController
class DeployDemoController {
	@Api(
		path = "/common/deploy-demo",
		method = RequestMethod.GET,
		summary = "배포 버전 조회",
		description = "현재 실행 중인 버전과 Pod 이름을 조회합니다.",
	)
	fun version(): ResponseEntity<DeployDemoOutDto> {
		return ResponseEntity.ok().body(
			DeployDemoOutDto(
				version = "team-v2",
				pod = System.getenv("HOSTNAME") ?: "local",
			),
		)
	}
}

data class DeployDemoOutDto(
	val version: String,
	val pod: String,
)
