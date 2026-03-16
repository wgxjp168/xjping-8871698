package com.ilbuy.reportgen;

import com.ilbuy.reportgen.client.L5ReportClient;
import com.ilbuy.reportgen.model.dto.GeneratedReport;
import com.ilbuy.reportgen.model.dto.ReportGenerateEvent;
import com.ilbuy.reportgen.model.enums.ClientType;
import com.ilbuy.reportgen.model.enums.ReportBusinessType;
import com.ilbuy.reportgen.service.generator.B2CDefinedBrandReportGenerator;
import com.ilbuy.reportgen.service.generator.B2CUndefinedBrandReportGenerator;
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
class B2CGeneratorTest {

    @Mock
    private L5ReportClient l5ReportClient;

    @InjectMocks
    private B2CDefinedBrandReportGenerator definedGen;

    @InjectMocks
    private B2CUndefinedBrandReportGenerator undefinedGen;

    @BeforeEach
    void setUp() {
        when(l5ReportClient.fetchReportData(anyString())).thenReturn(Map.of(
                "brandName", "TestBrand",
                "brandScore", 85,
                "brandAvgPrice", 299,
                "categoryAvgPrice", 250,
                "categoryName", "手机数码",
                "marketSize", "1200亿元",
                "activeBrandCount", 150
        ));
    }

    // ---- B2C Defined Brand ----

    @Test
    void definedGen_supports_B2C_DEFINED() {
        assertThat(definedGen.supports()).isEqualTo(ClientType.B2C_DEFINED);
    }

    @Test
    void definedGen_generatesSixSections() {
        ReportGenerateEvent event = buildEvent(ClientType.B2C_DEFINED, 500L);
        GeneratedReport report = definedGen.generate(event);

        assertThat(report.getSections()).hasSize(6);
        assertThat(report.getClientType()).isEqualTo(ClientType.B2C_DEFINED);
        assertThat(report.getBrandId()).isEqualTo(500L);
    }

    @Test
    void definedGen_priceComparisonHasCharts() {
        ReportGenerateEvent event = buildEvent(ClientType.B2C_DEFINED, 500L);
        GeneratedReport report = definedGen.generate(event);

        var priceSection = report.getSections().stream()
                .filter(s -> "PRICE_COMPARISON".equals(s.getSectionKey()))
                .findFirst().orElseThrow();

        assertThat(priceSection.getCharts()).isNotEmpty();
    }

    // ---- B2C Undefined Brand ----

    @Test
    void undefinedGen_supports_B2C_UNDEFINED() {
        assertThat(undefinedGen.supports()).isEqualTo(ClientType.B2C_UNDEFINED);
    }

    @Test
    void undefinedGen_generatesSixSections() {
        ReportGenerateEvent event = buildEvent(ClientType.B2C_UNDEFINED, null);
        GeneratedReport report = undefinedGen.generate(event);

        assertThat(report.getSections()).hasSize(6);
        assertThat(report.getClientType()).isEqualTo(ClientType.B2C_UNDEFINED);
        assertThat(report.getBrandId()).isNull();
    }

    @Test
    void undefinedGen_brandDiscoverySectionExists() {
        ReportGenerateEvent event = buildEvent(ClientType.B2C_UNDEFINED, null);
        GeneratedReport report = undefinedGen.generate(event);

        boolean hasBrandDiscovery = report.getSections().stream()
                .anyMatch(s -> "BRAND_DISCOVERY".equals(s.getSectionKey()));
        assertThat(hasBrandDiscovery).isTrue();
    }

    private ReportGenerateEvent buildEvent(ClientType clientType, Long brandId) {
        return ReportGenerateEvent.builder()
                .l5ReportNo("RPT-TEST-001")
                .userId(200L)
                .clientType(clientType)
                .businessType(ReportBusinessType.MARKET_TREND)
                .categoryId(3001L)
                .brandId(brandId)
                .title("Test Report")
                .parameters(Map.of())
                .generateHtml(true)
                .generatePdf(true)
                .build();
    }
}
