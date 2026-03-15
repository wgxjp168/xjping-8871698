package com.ilbuy.datasvc.api;

import com.ilbuy.datasvc.model.dto.SearchRequest;
import com.ilbuy.datasvc.model.dto.SearchResponse;
import com.ilbuy.datasvc.service.CacheService;
import com.ilbuy.datasvc.service.ProductSearchService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * 商品检索接口 — L5 业务层调用（预留）
 *
 * GET  /products/search?keyword=手机&platform=jd&page=0&size=20
 * POST /products/search  (JSON body SearchRequest)
 */
@RestController
@RequestMapping("/products")
@RequiredArgsConstructor
public class SearchController {

    private final ProductSearchService searchService;
    private final CacheService         cacheService;

    @GetMapping("/search")
    public ResponseEntity<SearchResponse> searchGet(
            @RequestParam String keyword,
            @RequestParam(required = false) String platform,
            @RequestParam(required = false) String brand,
            @RequestParam(required = false) String grade,
            @RequestParam(required = false) Boolean inStockOnly,
            @RequestParam(defaultValue = "0")  int page,
            @RequestParam(defaultValue = "20") int size) {

        SearchRequest req = new SearchRequest();
        req.setKeyword(keyword);
        req.setPlatform(platform);
        req.setBrand(brand);
        req.setGrade(grade);
        req.setInStockOnly(inStockOnly);
        req.setPage(page);
        req.setSize(size);
        return ResponseEntity.ok(searchService.search(req));
    }

    @PostMapping("/search")
    public ResponseEntity<SearchResponse> searchPost(@Valid @RequestBody SearchRequest request) {
        return ResponseEntity.ok(searchService.search(request));
    }

    @GetMapping("/{canonicalId}/cache")
    public ResponseEntity<String> getCachedProduct(@PathVariable String canonicalId) {
        return cacheService.getProductJson(canonicalId)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }
}
