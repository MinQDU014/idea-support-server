package com.ideasupport.lib.common.component
import org.springframework.stereotype.Component
import java.security.MessageDigest
import java.text.Normalizer
import java.util.Locale
import com.ideasupport.lib.common.enum.INTERNAL_ERROR_CODE
import com.ideasupport.lib.common.exception.ServerErrorException

@Component
class ContentPolicyComponent {
	// 호환 문자를 통일하고, 눈에 보이지 않는 서식 문자(폭 없는 공백 등)를 지운 뒤 공백을 하나로 줄인다.
	fun normalize(value: String): String =
		Normalizer.normalize(value, Normalizer.Form.NFKC)
			.replace(INVISIBLE_CHARACTERS, "")
			.trim()
			.replace(WHITESPACE_RUN, " ")

	fun key(value: String): String = normalize(value).lowercase(Locale.ROOT).replace(" ", "")

	fun hash(value: String): String =
		MessageDigest.getInstance("SHA-256").digest(value.toByteArray(Charsets.UTF_8)).joinToString("") {
			"%02x".format(it)
		}

	fun check(value: String) {
		val key = key(value)
		if (UNSAFE_PHRASE_KEYS.any { key.contains(it) }) {
			throw ServerErrorException(INTERNAL_ERROR_CODE.UNSAFE_CONTENT)
		}
	}

	fun requireInput(condition: Boolean) {
		if (!condition) throw ServerErrorException(INTERNAL_ERROR_CODE.INVALID_INPUT)
	}

	private companion object {
		val INVISIBLE_CHARACTERS = Regex("\\p{Cf}")
		val WHITESPACE_RUN = Regex("\\s+")
		val UNSAFE_PHRASES = listOf("폭탄 제조", "자살 방법")

		// 위험 문구도 입력과 같은 방식으로 정규화해서 비교한다.
		val UNSAFE_PHRASE_KEYS = UNSAFE_PHRASES.map { it.replace(" ", "").lowercase(Locale.ROOT) }
	}
}
