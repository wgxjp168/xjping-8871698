package com.ilbuy.reportgen;

import com.ilbuy.reportgen.client.L5ReportClient;
import com.ilbuy.reportgen.model.dto.GeneratedReport;
import com.ilbuy.reportgen.model.dto.ReportGenerateEvent;
import com.ilbuy.reportgen.model.enums.ClientType;
import com.ilbuy.reportgen.model.enums.ReportBusinessType;
import com.ilbuy.reportgen.service.generator.B2BReportGenerator;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class B2BReportGeneratorTest {

    @Mock
    private L5ReportClient l5ReportClient;

    @Mock
    private ObjectMapper objectMapper;

    @InjectMocks
    private B2BReportGenerator generator;

    private ReportGenerateEvent event;

    @BeforeEach
    void setUp() {
        when(l5ReportClient.fetchReportData(anyString())).thenReturn(Map.of(
                "supplierCount", 42,
                "avgPriceDeviation", 5.3,
                "complianceRisk", "LOW",
                "marketAvgPrice", 1000,
                "complianceScore", 88
        ));

        event = ReportGenerateEvent.builder()
                .l5ReportNo("RPT-20240101-001")
                .userId(100L)
                .clientType(ClientType.B2B)
                .businessType(ReportBusinessType.PRICE_ANALYSIS)
                .categoryId(2001L)
                .title("B2B Price Analysis Q1 2024")
                .parameters(Map.of("category", "electronics"))
                .generateHtml(true)
                .generatePdf(true)
                .generateExcel(true)
                .deliverEmail(true)
                .emailAddress("buyer@corp.com")
                .build();
    }

    @Test
    void supports_returnsB2B() {
        assertThat(generator.supports()).isEqualTo(ClientType.B2B);
    }

    @Test
    void generate_producesSixSections() {
        GeneratedReport report = generator.generate(event);

        assertThat(report).isNotNull();
        assertThat(report.getSections()).hasSize(6);
        assertThat(report.getClientType()).isEqualTo(ClientType.B2B);
        assertThat(report.getUserId()).isEqualTo(100L);
    }

    @Test
    void generate_executiveSummaryHasKeyFindings() {
        GeneratedReport report = generator.generate(event);

        var summary = report.getSections().stream()
                .filter(s -> "EXECUTIVE_SUMMARY".equals(s.getSectionKey()))
                .findFirst()
                .orElseThrow();

        assertThat(summary.getContent()).containsKey("keyFindings");
        assertThat(summary.getOrderIndex()).isEqualTo(0);
    }

    @Test
    void generate_supplierLandscapeHasCharts() {
        GeneratedReport report = generator.generate(event);

        var landscape = report.getSections().stream()
                .filter(s -> "SUPPLIER_LANDSCAPE".equals(s.getSectionKey()))
                .findFirst()
                .orElseThrow();

        assertThat(landscape.getCharts()).isNotEmpty();
        assertThat(landscape.getCharts().get(0).getType()).isEqualTo("pie");
    }

    @Test
    void generate_metadataHasGeneratorVersion() {
        GeneratedReport report = generator.generate(event);
        assertThat(report.getMetadata()).containsKey("generatorVersion");
        assertThat(report.getMetadata().get("generatorVersion")).isEqualTo("B2B-v1.0");
    }

    @Test
    void generate_formatFlagsPreserved() {
        GeneratedReport report = generator.generate(event);
        assertThat(report.isGenerateHtml()).isTrue();
        assertThat(report.isGeneratePdf()).isTrue();
        assertThat(report.isGenerateExcel()).isTrue();
        assertThat(report.isDeliverEmail()).isTrue();
        assertThat(report.getEmailAddress()).isEqualTo("buyer@corp.com");
    }
}
