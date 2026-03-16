package com.ilbuy.product.api;

import com.ilbuy.product.model.dto.*;
import com.ilbuy.product.service.ProductService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.List;

@RestController
@RequestMapping("/api/v1/products")
@RequiredArgsConstructor
public class ProductController {

    private final ProductService productService;

    /**
     * Keyword search across all products.
     * Public — no authentication required (gateway whitelist).
     *
     * GET /api/v1/products/search?keyword=iphone&categoryId=1&minPrice=100&maxPrice=9999
     *     &platform=jd&page=0&size=20&sortBy=price_asc
     */
    @GetMapping("/search")
    public ResponseEntity<PageResult<ProductDTO>> search(
        @RequestParam(required = false) String keyword,
        @RequestParam(required = false) Long categoryId,
        @RequestParam(required = false) BigDecimal minPrice,
        @RequestParam(required = false) BigDecimal maxPrice,
        @RequestParam(required = false) String platform,
        @RequestParam(defaultValue = "0")  int page,
        @RequestParam(defaultValue = "20") int size,
        @RequestParam(defaultValue = "relevance") String sortBy
    ) {
        ProductSearchRequest req = new ProductSearchRequest();
        req.setKeyword(keyword);
        req.setCategoryId(categoryId);
        req.setMinPrice(minPrice);
        req.setMaxPrice(maxPrice);
        req.setPlatform(platform);
        req.setPage(page);
        req.setSize(size);
        req.setSortBy(sortBy);
        return ResponseEntity.ok(productService.searchProducts(req));
    }

    /**
     * Full product detail including all platform listings.
     * Public — no authentication required.
     *
     * GET /api/v1/products/{id}/detail
     */
    @GetMapping("/{id}/detail")
    public ResponseEntity<ProductDetailDTO> getDetail(@PathVariable Long id) {
        return ResponseEntity.ok(productService.getProductDetail(id));
    }

    /**
     * Cross-platform price comparison for one canonical product.
     * Returns all platform listings sorted cheapest first.
     * Public — no authentication required.
     *
     * GET /api/v1/products/{canonicalId}/platforms
     */
    @GetMapping("/{canonicalId}/platforms")
    public ResponseEntity<List<PlatformListingDTO>> getPlatforms(
        @PathVariable String canonicalId
    ) {
        return ResponseEntity.ok(productService.getPlatformComparison(canonicalId));
    }

    /**
     * Browse the full category tree.
     * Public — no authentication required.
     *
     * GET /api/v1/products/categories
     */
    @GetMapping("/categories")
    public ResponseEntity<List<CategoryDTO>> getCategories() {
        return ResponseEntity.ok(productService.getCategories());
    }

    /**
     * Paginated list of products under a specific category.
     * Public — no authentication required.
     *
     * GET /api/v1/products/categories/{id}?page=0&size=20
     */
    @GetMapping("/categories/{id}")
    public ResponseEntity<PageResult<ProductDTO>> getProductsByCategory(
        @PathVariable Long id,
        @RequestParam(defaultValue = "0")  int page,
        @RequestParam(defaultValue = "20") int size
    ) {
        return ResponseEntity.ok(productService.getProductsByCategory(id, page, size));
    }

    /**
     * Side-by-side comparison of up to 4 products.
     * Requires authentication (POST body: {"ids": [1, 2, 3, 4]}).
     *
     * POST /api/v1/products/compare
     */
    @PostMapping("/compare")
    public ResponseEntity<List<ProductDetailDTO>> compare(
        @AuthenticationPrincipal Long userId,
        @Valid @RequestBody CompareRequest request
    ) {
        return ResponseEntity.ok(productService.compareProducts(request.getIds()));
    }
}
