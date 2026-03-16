package com.ilbuy.format.service.formatter;

import com.ilbuy.format.model.dto.FormatJobRequest;
import com.lowagie.text.DocumentException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.thymeleaf.TemplateEngine;
import org.thymeleaf.context.Context;
import org.xhtmlrenderer.pdf.ITextRenderer;

import java.io.ByteArrayOutputStream;
import java.time.OffsetDateTime;
import java.util.Locale;

/**
 * PDF Formatter – renders the HTML template through Flying Saucer → PDF.
 * Supports CJK characters via embedded NotoSansSC font (auto-detected from classpath).
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class PdfFormatter {

    private final TemplateEngine templateEngine;

    public byte[] format(FormatJobRequest request) throws DocumentException {
        log.debug("[PdfFormatter] Rendering PDF for jobNo={}", request.getJobNo());

        // 1. Render HTML (no chart.js for PDF – static summary)
        Context ctx = new Context(Locale.CHINESE);
        ctx.setVariable("report", request);
        ctx.setVariable("pdfUrl", null);     // no self-reference in PDF
        ctx.setVariable("excelUrl", null);
        ctx.setVariable("generatedAt", OffsetDateTime.now());

        String html = templateEngine.process("report", ctx);

        // Strip Chart.js script tags for PDF rendering (static charts unsupported)
        html = html.replaceAll("(?s)<script[^>]*>.*?</script>", "");
        // Remove CDN links
        html = html.replaceAll("<script[^>]*src[^>]*cdn[^>]*>\\s*</script>", "");

        // 2. Flying Saucer HTML→PDF
        try (ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            ITextRenderer renderer = new ITextRenderer();
            renderer.setDocumentFromString(html);
            renderer.layout();
            renderer.createPDF(out);
            byte[] pdfBytes = out.toByteArray();
            log.debug("[PdfFormatter] PDF size={} bytes", pdfBytes.length);
            return pdfBytes;
        } catch (Exception e) {
            log.error("[PdfFormatter] Failed to render PDF: {}", e.getMessage(), e);
            throw new DocumentException("PDF generation failed: " + e.getMessage());
        }
    }
}
