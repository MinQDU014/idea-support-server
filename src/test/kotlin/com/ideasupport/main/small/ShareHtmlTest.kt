package com.ideasupport.main.small
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Assertions.*
import com.ideasupport.main.app.share.ShareHtmlComponent
import com.ideasupport.core.dto.app.idea.IdeaOutDto
import java.time.Instant

class ShareHtmlTest {
	@Test fun `공유된 내용으로 실행 가능한 HTML을 넣을 수 없다`() {
		val html =
			ShareHtmlComponent().render(
				IdeaOutDto("id", "category", emptyList(), "", "<script>alert(1)</script>", "<img src=x onerror=alert(2)>", null, "mock", false, Instant.now()),
				null,
			)
		assertFalse(html.contains("<script>"))
		assertFalse(html.contains("<img"))
		assertTrue(html.contains("&lt;script&gt;"))
	}
}
