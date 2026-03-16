package com.ilbuy.format.service.formatter;

import com.ilbuy.format.model.dto.FormatJobRequest;
import com.ilbuy.format.model.dto.SectionDTO;
import lombok.extern.slf4j.Slf4j;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.ss.util.CellRangeAddress;
import org.apache.poi.xssf.usermodel.*;
import org.springframework.stereotype.Component;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;

/**
 * Excel Formatter – generates multi-sheet XLSX report using Apache POI.
 * Sheet 0: Report Summary
 * Sheet N: one sheet per report section
 */
@Component
@Slf4j
public class ExcelFormatter {

    private static final DateTimeFormatter DATE_FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    public byte[] format(FormatJobRequest request) throws IOException {
        log.debug("[ExcelFormatter] Generating Excel for jobNo={}", request.getJobNo());

        try (XSSFWorkbook workbook = new XSSFWorkbook();
             ByteArrayOutputStream out = new ByteArrayOutputStream()) {

            CellStyle headerStyle = createHeaderStyle(workbook);
            CellStyle titleStyle = createTitleStyle(workbook);
            CellStyle metaStyle = createMetaStyle(workbook);

            // Sheet 0 – Summary
            buildSummarySheet(workbook, request, titleStyle, metaStyle, headerStyle);

            // One sheet per section
            if (request.getSections() != null) {
                for (SectionDTO section : request.getSections()) {
                    buildSectionSheet(workbook, section, headerStyle, metaStyle);
                }
            }

            workbook.write(out);
            byte[] bytes = out.toByteArray();
            log.debug("[ExcelFormatter] Excel size={} bytes", bytes.length);
            return bytes;
        }
    }

    private void buildSummarySheet(XSSFWorkbook wb, FormatJobRequest req,
                                   CellStyle titleStyle, CellStyle metaStyle, CellStyle headerStyle) {
        XSSFSheet sheet = wb.createSheet("报告摘要");
        sheet.setColumnWidth(0, 6000);
        sheet.setColumnWidth(1, 14000);

        int row = 0;

        Row titleRow = sheet.createRow(row++);
        titleRow.setHeightInPoints(30);
        Cell titleCell = titleRow.createCell(0);
        titleCell.setCellValue("我来购ILbuy 智能采购报告");
        titleCell.setCellStyle(titleStyle);
        sheet.addMergedRegion(new CellRangeAddress(0, 0, 0, 3));

        row++; // blank row

        Object[][] meta = {
            {"报告标题", req.getTitle()},
            {"报告编号", req.getL5ReportNo()},
            {"客户类型", req.getClientType()},
            {"业务类型", req.getBusinessType()},
            {"用户ID", req.getUserId()},
            {"品牌ID", req.getBrandId()},
            {"品类ID", req.getCategoryId()},
            {"生成时间", req.getGeneratedAt() != null ? req.getGeneratedAt().format(DATE_FMT) : "N/A"},
        };

        for (Object[] kv : meta) {
            Row r = sheet.createRow(row++);
            Cell k = r.createCell(0);
            k.setCellValue(String.valueOf(kv[0]));
            k.setCellStyle(headerStyle);
            Cell v = r.createCell(1);
            v.setCellValue(kv[1] != null ? String.valueOf(kv[1]) : "N/A");
            v.setCellStyle(metaStyle);
        }

        row++;
        Row sectionsHeader = sheet.createRow(row++);
        Cell sh = sectionsHeader.createCell(0);
        sh.setCellValue("报告章节列表");
        sh.setCellStyle(headerStyle);

        Row colRow = sheet.createRow(row++);
        colRow.createCell(0).setCellValue("章节Key");
        colRow.createCell(1).setCellValue("章节标题");
        colRow.createCell(2).setCellValue("图表数量");
        for (int c = 0; c < 3; c++) colRow.getCell(c).setCellStyle(headerStyle);

        if (req.getSections() != null) {
            for (SectionDTO s : req.getSections()) {
                Row sRow = sheet.createRow(row++);
                sRow.createCell(0).setCellValue(s.getSectionKey());
                sRow.createCell(1).setCellValue(s.getTitle());
                sRow.createCell(2).setCellValue(s.getCharts() == null ? 0 : s.getCharts().size());
            }
        }

        if (req.getMetadata() != null) {
            row++;
            Row mh = sheet.createRow(row++);
            mh.createCell(0).setCellValue("元数据 Metadata");
            mh.getCell(0).setCellStyle(headerStyle);
            for (Map.Entry<String, Object> entry : req.getMetadata().entrySet()) {
                Row mr = sheet.createRow(row++);
                mr.createCell(0).setCellValue(entry.getKey());
                mr.createCell(1).setCellValue(String.valueOf(entry.getValue()));
            }
        }
    }

    @SuppressWarnings("unchecked")
    private void buildSectionSheet(XSSFWorkbook wb, SectionDTO section,
                                   CellStyle headerStyle, CellStyle metaStyle) {
        // Sanitize sheet name (Excel limit: 31 chars, no special chars)
        String sheetName = section.getTitle().length() > 28
                ? section.getTitle().substring(0, 28)
                : section.getTitle();
        sheetName = sheetName.replaceAll("[\\[\\]\\*\\/\\\\\\?\\:]", "_");

        XSSFSheet sheet = wb.createSheet(sheetName);
        sheet.setColumnWidth(0, 8000);
        sheet.setColumnWidth(1, 18000);

        int row = 0;

        Row titleRow = sheet.createRow(row++);
        Cell tc = titleRow.createCell(0);
        tc.setCellValue(section.getTitle());
        tc.setCellStyle(headerStyle);
        sheet.addMergedRegion(new CellRangeAddress(0, 0, 0, 3));

        row++;

        // Content key-value pairs
        if (section.getContent() != null) {
            Row contentHeader = sheet.createRow(row++);
            contentHeader.createCell(0).setCellValue("字段 Field");
            contentHeader.createCell(1).setCellValue("值 Value");
            contentHeader.getCell(0).setCellStyle(headerStyle);
            contentHeader.getCell(1).setCellStyle(headerStyle);

            for (Map.Entry<String, Object> entry : section.getContent().entrySet()) {
                Row dr = sheet.createRow(row++);
                dr.createCell(0).setCellValue(entry.getKey());
                Object val = entry.getValue();
                if (val instanceof List) {
                    dr.createCell(1).setCellValue(String.join("; ", ((List<Object>) val).stream()
                            .map(Object::toString).toList()));
                } else if (val instanceof Map) {
                    dr.createCell(1).setCellValue(val.toString());
                } else {
                    dr.createCell(1).setCellValue(val != null ? String.valueOf(val) : "");
                }
            }
        }

        // Charts data summary
        if (section.getCharts() != null && !section.getCharts().isEmpty()) {
            row++;
            Row chartHeader = sheet.createRow(row++);
            chartHeader.createCell(0).setCellValue("图表数据 Chart Data");
            chartHeader.getCell(0).setCellStyle(headerStyle);

            for (var chart : section.getCharts()) {
                row++;
                Row cr = sheet.createRow(row++);
                cr.createCell(0).setCellValue("图表: " + chart.getTitle());
                cr.createCell(1).setCellValue("类型: " + chart.getType());

                if (chart.getLabels() != null && chart.getDatasets() != null) {
                    Row labelsRow = sheet.createRow(row++);
                    labelsRow.createCell(0).setCellValue("标签");
                    int col = 1;
                    for (String label : chart.getLabels()) {
                        labelsRow.createCell(col++).setCellValue(label);
                    }
                    for (Map<String, Object> dataset : chart.getDatasets()) {
                        Row dataRow = sheet.createRow(row++);
                        dataRow.createCell(0).setCellValue(String.valueOf(dataset.get("label")));
                        List<Object> data = (List<Object>) dataset.get("data");
                        if (data != null) {
                            int c = 1;
                            for (Object d : data) {
                                Cell cell = dataRow.createCell(c++);
                                if (d instanceof Number) {
                                    cell.setCellValue(((Number) d).doubleValue());
                                } else {
                                    cell.setCellValue(String.valueOf(d));
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    private CellStyle createHeaderStyle(XSSFWorkbook wb) {
        CellStyle style = wb.createCellStyle();
        XSSFFont font = wb.createFont();
        font.setBold(true);
        font.setFontHeightInPoints((short) 11);
        style.setFont(font);
        style.setFillForegroundColor(IndexedColors.ROYAL_BLUE.getIndex());
        style.setFillPattern(FillPatternType.SOLID_FOREGROUND);
        style.setFontColor(IndexedColors.WHITE.getIndex());
        style.setBorderBottom(BorderStyle.THIN);
        style.setAlignment(HorizontalAlignment.LEFT);
        // font color must be set on font directly
        XSSFFont whiteFont = wb.createFont();
        whiteFont.setBold(true);
        whiteFont.setColor(IndexedColors.WHITE.getIndex());
        whiteFont.setFontHeightInPoints((short) 11);
        style.setFont(whiteFont);
        return style;
    }

    private CellStyle createTitleStyle(XSSFWorkbook wb) {
        CellStyle style = wb.createCellStyle();
        XSSFFont font = wb.createFont();
        font.setBold(true);
        font.setFontHeightInPoints((short) 16);
        style.setFont(font);
        style.setAlignment(HorizontalAlignment.CENTER);
        return style;
    }

    private CellStyle createMetaStyle(XSSFWorkbook wb) {
        CellStyle style = wb.createCellStyle();
        style.setWrapText(true);
        return style;
    }

    private void setFontColor(CellStyle style, short color) {
        // No-op helper (handled inline above)
    }
}
