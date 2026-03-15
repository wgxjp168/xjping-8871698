package com.ilbuy.datasvc.service;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch._types.SortOrder;
import co.elastic.clients.elasticsearch._types.query_dsl.Query;
import co.elastic.clients.elasticsearch.core.SearchRequest;
import co.elastic.clients.elasticsearch.core.SearchResponse;
import co.elastic.clients.elasticsearch.core.search.Hit;
import com.ilbuy.datasvc.model.document.ProductDocument;
import com.ilbuy.datasvc.model.dto.ProductSummaryDTO;
import com.ilbuy.datasvc.model.dto.SearchResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

/**
 * Elasticsearch 全文检索服务
 *
 * 搜索策略：
 *  1. multi_match: title_cleaned + title (boost: 2 / 1)
 *  2. filter: platform / brand / price_range / grade / in_stock
 *  3. sort: total_score DESC (默认) 或指定字段
 *  4. pagination: page/size
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class ProductSearchService {

    private final ElasticsearchClient esClient;

    private static final String INDEX = "ilbuy_products";

    public SearchResponse search(com.ilbuy.datasvc.model.dto.SearchRequest req) {
        long t0 = System.currentTimeMillis();

        try {
            SearchRequest esReq = SearchRequest.of(sr -> {
                sr.index(INDEX)
                  .from(req.getPage() * req.getSize())
                  .size(req.getSize());

                // ── 构建查询 ────────────────────────────────────────
                List<Query> filters = new ArrayList<>();

                // 全文匹配
                Query mainQuery = Query.of(q -> q.multiMatch(mm -> mm
                    .fields("title_cleaned^2", "title", "brand_normalised")
                    .query(req.getKeyword())
                    .fuzziness("AUTO")
                ));

                // 过滤条件
                if (req.getPlatform() != null) {
                    filters.add(Query.of(q -> q.term(t -> t
                        .field("platform").value(req.getPlatform()))));
                }
                if (req.getBrand() != null) {
                    filters.add(Query.of(q -> q.term(t -> t
                        .field("brandNormalised").value(req.getBrand()))));
                }
                if (req.getGrade() != null) {
                    filters.add(Query.of(q -> q.term(t -> t
                        .field("grade").value(req.getGrade()))));
                }
                if (Boolean.TRUE.equals(req.getInStockOnly())) {
                    filters.add(Query.of(q -> q.term(t -> t
                        .field("inStock").value(true))));
                }
                if (req.getPriceMin() != null || req.getPriceMax() != null) {
                    final BigDecimal min = req.getPriceMin();
                    final BigDecimal max = req.getPriceMax();
                    filters.add(Query.of(q -> q.range(r -> {
                        r.field("price");
                        if (min != null) r.gte(co.elastic.clients.json.JsonData.of(min));
                        if (max != null) r.lte(co.elastic.clients.json.JsonData.of(max));
                        return r;
                    })));
                }

                // bool query
                final List<Query> finalFilters = filters;
                sr.query(q -> q.bool(b -> b
                    .must(mainQuery)
                    .filter(finalFilters)
                ));

                // ── 排序 ───────────────────────────────────────────
                String sortField = req.getSortBy() != null ? req.getSortBy() : "totalScore";
                SortOrder order  = "asc".equalsIgnoreCase(req.getSortOrder())
                    ? SortOrder.Asc : SortOrder.Desc;
                sr.sort(s -> s.field(f -> f.field(sortField).order(order)));

                return sr;
            });

            SearchResponse<ProductDocument> esResp = esClient.search(esReq, ProductDocument.class);

            List<ProductSummaryDTO> items = esResp.hits().hits().stream()
                .map(Hit::source)
                .filter(doc -> doc != null)
                .map(this::toSummary)
                .toList();

            long took = System.currentTimeMillis() - t0;
            long total = esResp.hits().total() != null ? esResp.hits().total().value() : 0;

            return com.ilbuy.datasvc.model.dto.SearchResponse.builder()
                .total(total)
                .page(req.getPage())
                .size(req.getSize())
                .tookMs(took)
                .items(items)
                .build();

        } catch (Exception e) {
            log.error("ES search failed keyword={}: {}", req.getKeyword(), e.getMessage());
            return com.ilbuy.datasvc.model.dto.SearchResponse.builder()
                .total(0).page(req.getPage()).size(req.getSize())
                .tookMs(System.currentTimeMillis() - t0)
                .items(List.of())
                .build();
        }
    }

    private ProductSummaryDTO toSummary(ProductDocument doc) {
        ProductSummaryDTO s = new ProductSummaryDTO();
        s.setCanonicalId(doc.getCanonicalId());
        s.setPlatform(doc.getPlatform());
        s.setTitle(doc.getTitleCleaned() != null ? doc.getTitleCleaned() : doc.getTitle());
        s.setPrice(doc.getPrice());
        s.setOriginalPrice(doc.getOriginalPrice());
        s.setDiscountPct(doc.getDiscountPct());
        s.setBrand(doc.getBrandNormalised());
        s.setGrade(doc.getGrade());
        s.setTotalScore(doc.getTotalScore());
        s.setAverageRating(doc.getAverageRating());
        s.setReviewCount(doc.getReviewCount());
        s.setInStock(doc.getInStock());
        s.setThumbnailUrl(doc.getImages() != null && !doc.getImages().isEmpty()
            ? doc.getImages().get(0) : null);
        s.setUrl(doc.getUrl());
        s.setCrawledAt(doc.getCrawledAt() != null ? doc.getCrawledAt().toString() : null);
        return s;
    }
}
