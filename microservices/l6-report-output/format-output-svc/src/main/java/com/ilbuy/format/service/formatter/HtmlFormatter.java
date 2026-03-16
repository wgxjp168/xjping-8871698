package com.ilbuy.format.service.formatter;

import com.ilbuy.format.model.dto.FormatJobRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.thymeleaf.TemplateEngine;
import org.thymeleaf.context.Context;

import java.time.OffsetDateTime;
import java.util.Locale;

/**
 * HTML Formatter – renders interactive Thymeleaf report.
 * Output: full HTML string (stored to MinIO as .html file).
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class HtmlFormatter {

    private final TemplateEngine templateEngine;

    public byte[] format(FormatJobRequest request, String pdfUrl, String excelUrl) {
        log.debug("[HtmlFormatter] Rendering HTML for jobNo={}", request.getJobNo());

        Context ctx = new Context(Locale.CHINESE);
        ctx.setVariable("report", request);
        ctx.setVariable("pdfUrl", pdfUrl);
        ctx.setVariable("excelUrl", excelUrl);
        ctx.setVariable("generatedAt", OffsetDateTime.now());

        String html = templateEngine.process("report", ctx);

        log.debug("[HtmlFormatter] Rendered {} chars", html.length());
        return html.getBytes(java.nio.charset.StandardCharsets.UTF_8);
    }
}
