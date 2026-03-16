package com.ilbuy.report.api;

import com.ilbuy.report.model.entity.Report;
import com.ilbuy.report.repository.ReportRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Internal API for L6 report-generator-svc.
 * Provides enriched report data that the generator uses to build section content.
 * Secured at network layer (ClusterIP only – not exposed via Ingress).
 */
@RestController
@RequestMapping("/internal/v1/reports")
@RequiredArgsConstructor
@Slf4j
public class InternalReportController {

    private final ReportRepository reportRepository;

    /**
     * GET /internal/v1/reports/{reportNo}/data
     * Returns enriched data for report generation.
     * L6 report-generator-svc calls this to get contextual data per report type.
     */
    @GetMapping("/{reportNo}/data")
    public ResponseEntity<Map<String, Object>> getReportData(@PathVariable String reportNo) {
        log.info("[Internal] Data fetch for reportNo={}", reportNo);

        Report report = reportRepository.findByReportNoAndDeletedFalse(reportNo)
                .orElseThrow(() -> new IllegalArgumentException("Report not found: " + reportNo));

        Map<String, Object> data = buildEnrichedData(report);
        return ResponseEntity.ok(data);
    }

    /**
     * GET /internal/v1/reports/{reportNo}/status
     * Lightweight status probe for L6 to check before generating.
     */
    @GetMapping("/{reportNo}/status")
    public ResponseEntity<Map<String, Object>> getReportStatus(@PathVariable String reportNo) {
        Report report = reportRepository.findByReportNoAndDeletedFalse(reportNo)
                .orElseThrow(() -> new IllegalArgumentException("Report not found: " + reportNo));

        return ResponseEntity.ok(Map.of(
                "reportNo",  report.getReportNo(),
                "status",    report.getStatus(),
                "type",      report.getType(),
                "userId",    report.getUserId(),
                "title",     report.getTitle()
        ));
    }

    /**
     * Builds enriched data map for L6 generation.
     * In production, this would aggregate from:
     *  - Product service (prices, categories)
     *  - Supplier service (supplier profiles)
     *  - Market data service (trends, sentiment)
     *  - Recommendation service (ranked lists)
     *
     * The stub below returns type-appropriate mock data that generators can use
     * as defaults when real data from downstream services is unavailable.
     */
    private Map<String, Object> buildEnrichedData(Report report) {
        Map<String, Object> data = new HashMap<>();

        // Base metadata
        data.put("reportNo",       report.getReportNo());
        data.put("reportType",     report.getType().name());
        data.put("userId",         report.getUserId());
        data.put("title",          report.getTitle());
        data.put("reportPeriod",   "Last 90 days");
        data.put("dataAsOf",       java.time.OffsetDateTime.now().toString());

        // Type-specific enrichment
        switch (report.getType()) {
            case PRICE_ANALYSIS -> enrichPriceAnalysis(data);
            case SUPPLIER_EVAL  -> enrichSupplierEval(data);
            case MARKET_TREND   -> enrichMarketTrend(data);
        }

        return data;
    }

    private void enrichPriceAnalysis(Map<String, Object> data) {
        data.put("marketAvgPrice",      1580.00);
        data.put("priceRange",          Map.of("min", 980, "max", 3200));
        data.put("avgPriceDeviation",   4.8);
        data.put("savingsPotential",    "8-15%");
        data.put("priceDataPoints",     12450);
        data.put("quarterlyPriceTrend", List.of(1620, 1590, 1550, 1580));
        data.put("volumeDiscounts",     List.of(
                Map.of("minQty", 100, "discount", "5%"),
                Map.of("minQty", 500, "discount", "10%"),
                Map.of("minQty", 1000, "discount", "15%")
        ));
        data.put("brandAvgPrice",       1680.00);
        data.put("categoryAvgPrice",    1580.00);
        data.put("premiumPercent",      "6.3%");
        data.put("priceHistory",        List.of(
                Map.of("date", "2024-01", "price", 1620),
                Map.of("date", "2024-02", "price", 1595),
                Map.of("date", "2024-03", "price", 1580)
        ));
    }

    private void enrichSupplierEval(Map<String, Object> data) {
        data.put("supplierCount",    47);
        data.put("tier1Count",       8);
        data.put("tier2Count",       19);
        data.put("tier3Count",       20);
        data.put("tier1Suppliers",   List.of(
                Map.of("id", 1001, "name", "供应商A", "score", 96, "onTimeRate", "98.5%"),
                Map.of("id", 1002, "name", "供应商B", "score", 94, "onTimeRate", "97.2%")
        ));
        data.put("geoDistribution",  Map.of("华东", 18, "华南", 14, "华北", 9, "西部", 4, "海外", 2));
        data.put("complianceScore",  87);
        data.put("complianceRisk",   "LOW");
        data.put("esgScore",         Map.of("environmental", 80, "social", 75, "governance", 90));
        data.put("overallRisk",      "MEDIUM");
        data.put("estimatedSavings", "10-14%");
        data.put("prioritySuppliers", List.of(1001, 1002, 1003));
        data.put("auditHistory",     List.of(
                Map.of("date", "2024-Q1", "result", "PASS", "auditor", "Bureau Veritas"),
                Map.of("date", "2023-Q3", "result", "PASS", "auditor", "SGS")
        ));
    }

    private void enrichMarketTrend(Map<String, Object> data) {
        data.put("marketSize",         "1,280亿元");
        data.put("marketGrowthRate",   "12.5% YoY");
        data.put("activeBrandCount",   182);
        data.put("activeProductCount", 54600);
        data.put("marketDrivers",      List.of("消费升级", "数字化采购", "跨境电商增长"));
        data.put("hotSubcategories",   List.of("智能家居", "健康保健", "新能源"));
        data.put("emergingTrends",     List.of("可持续消费", "国产品牌崛起", "即时配送"));
        data.put("sentimentScore",     74);
        data.put("overallSentiment",   "POSITIVE");
        data.put("positiveKeywords",   List.of("性价比高", "质量可靠", "配送快"));
        data.put("negativeKeywords",   List.of("售后待改善", "包装简单"));
        data.put("consumerProfiles",   Map.of(
                "ageGroup",  "25-40岁",
                "topCities", List.of("上海", "北京", "深圳", "成都")
        ));
        data.put("recommendedBudget",  "200-600元");
        data.put("sweetSpotRange",     "250-450元");
        data.put("topBrandName",       "品牌A");
        data.put("topBrandId",         5001L);
        data.put("topBrandPrice",      358);
        data.put("risingBrandName",    "品牌B");
        data.put("risingBrandId",      5002L);
        data.put("risingBrandPrice",   288);
    }
}
