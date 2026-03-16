package com.ilbuy.format;

import com.ilbuy.format.model.dto.ChartDTO;
import com.ilbuy.format.model.dto.FormatJobRequest;
import com.ilbuy.format.model.dto.SectionDTO;
import com.ilbuy.format.service.formatter.ExcelFormatter;
import org.apache.poi.ss.usermodel.Workbook;
import org.apache.poi.ss.usermodel.WorkbookFactory;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayInputStream;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class ExcelFormatterTest {

    private ExcelFormatter formatter;
    private FormatJobRequest request;

    @BeforeEach
    void setUp() {
        formatter = new ExcelFormatter();

        SectionDTO section1 = new SectionDTO();
        section1.setSectionKey("EXECUTIVE_SUMMARY");
        section1.setTitle("执行摘要 Executive Summary");
        section1.setContent(Map.of(
                "overview", "Test overview",
                "reportPeriod", "Q1 2024"
        ));
        section1.setCharts(List.of());
        section1.setOrderIndex(0);

        ChartDTO chart = new ChartDTO();
        chart.setChartId("test-chart");
        chart.setType("bar");
        chart.setTitle("Test Chart");
        chart.setLabels(List.of("A", "B", "C"));
        chart.setDatasets(List.of(Map.of("label", "Series 1", "data", List.of(10, 20, 30))));

        SectionDTO section2 = new SectionDTO();
        section2.setSectionKey("SUPPLIER_LANDSCAPE");
        section2.setTitle("供应商格局");
        section2.setContent(Map.of("totalSuppliers", 42));
        section2.setCharts(List.of(chart));
        section2.setOrderIndex(1);

        request = new FormatJobRequest();
        request.setJobNo("GEN-TESTJOB001");
        request.setL5ReportNo("RPT-20240101-001");
        request.setUserId(100L);
        request.setTitle("Test B2B Report");
        request.setClientType("B2B");
        request.setBusinessType("PRICE_ANALYSIS");
        request.setCategoryId(2001L);
        request.setGeneratedAt(OffsetDateTime.now());
        request.setSections(List.of(section1, section2));
        request.setMetadata(Map.of("generatorVersion", "B2B-v1.0"));
    }

    @Test
    void format_producesValidXlsx() throws Exception {
        byte[] bytes = formatter.format(request);

        assertThat(bytes).isNotEmpty();
        assertThat(bytes.length).isGreaterThan(1000);

        // Verify it's a valid XLSX file
        try (Workbook wb = WorkbookFactory.create(new ByteArrayInputStream(bytes))) {
            assertThat(wb.getNumberOfSheets()).isEqualTo(3); // Summary + 2 sections
        }
    }

    @Test
    void format_summarySheetNameCorrect() throws Exception {
        byte[] bytes = formatter.format(request);

        try (Workbook wb = WorkbookFactory.create(new ByteArrayInputStream(bytes))) {
            assertThat(wb.getSheetAt(0).getSheetName()).isEqualTo("报告摘要");
        }
    }

    @Test
    void format_sectionSheetsExist() throws Exception {
        byte[] bytes = formatter.format(request);

        try (Workbook wb = WorkbookFactory.create(new ByteArrayInputStream(bytes))) {
            assertThat(wb.getSheetAt(1).getSheetName()).contains("执行摘要");
            assertThat(wb.getSheetAt(2).getSheetName()).contains("供应商格局");
        }
    }

    @Test
    void format_summaryContainsReportMeta() throws Exception {
        byte[] bytes = formatter.format(request);

        try (Workbook wb = WorkbookFactory.create(new ByteArrayInputStream(bytes))) {
            var sheet = wb.getSheetAt(0);
            // Check title row
            assertThat(sheet.getRow(0).getCell(0).getStringCellValue()).contains("我来购ILbuy");
        }
    }
}
