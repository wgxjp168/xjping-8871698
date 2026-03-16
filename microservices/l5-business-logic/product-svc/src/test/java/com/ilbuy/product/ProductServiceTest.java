package com.ilbuy.product;

import com.ilbuy.product.model.dto.*;
import com.ilbuy.product.model.entity.Category;
import com.ilbuy.product.model.entity.PlatformListing;
import com.ilbuy.product.model.entity.Product;
import com.ilbuy.product.repository.CategoryRepository;
import com.ilbuy.product.repository.PlatformListingRepository;
import com.ilbuy.product.repository.ProductRepository;
import com.ilbuy.product.service.ProductService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ProductServiceTest {

    @Mock ProductRepository         productRepository;
    @Mock PlatformListingRepository listingRepository;
    @Mock CategoryRepository        categoryRepository;

    ProductService productService;

    @BeforeEach
    void setUp() {
        productService = new ProductService(productRepository, listingRepository, categoryRepository);
    }

    // ── Fixture helpers ───────────────────────────────────────────────────────

    private Product buildProduct(Long id, String canonicalId, String name, Long categoryId) {
        return Product.builder()
            .id(id)
            .canonicalId(canonicalId)
            .name(name)
            .brand("TestBrand")
            .categoryId(categoryId)
            .referencePrice(new BigDecimal("999.00"))
            .enabled(true)
            .createdAt(Instant.now())
            .updatedAt(Instant.now())
            .build();
    }

    private PlatformListing buildListing(Long id, String canonicalId,
                                         String platform, String price) {
        return PlatformListing.builder()
            .id(id)
            .canonicalId(canonicalId)
            .platform(platform)
            .externalUrl("https://" + platform + ".com/product/" + id)
            .currentPrice(new BigDecimal(price))
            .originalPrice(new BigDecimal(price).multiply(new BigDecimal("1.2")))
            .currency("CNY")
            .inStock(true)
            .lastSyncAt(Instant.now())
            .build();
    }

    private Category buildCategory(Long id, String name, Long parentId) {
        return Category.builder()
            .id(id)
            .name(name)
            .parentId(parentId)
            .enabled(true)
            .sortOrder(0)
            .build();
    }

    // ── searchProducts ────────────────────────────────────────────────────────

    @Test
    void searchProducts_withKeyword_returnsMatchingPage() {
        Product p = buildProduct(1L, "canon-001", "iPhone 15 Pro", 10L);
        var pageResult = new PageImpl<>(List.of(p));

        when(productRepository.searchProducts(
            eq("iPhone"), isNull(), isNull(), isNull(), any(Pageable.class)
        )).thenReturn(pageResult);

        ProductSearchRequest req = new ProductSearchRequest();
        req.setKeyword("iPhone");

        PageResult<ProductDTO> result = productService.searchProducts(req);

        assertThat(result.getTotalElements()).isEqualTo(1);
        assertThat(result.getContent()).hasSize(1);
        assertThat(result.getContent().get(0).getName()).isEqualTo("iPhone 15 Pro");
        assertThat(result.getContent().get(0).getCanonicalId()).isEqualTo("canon-001");

        verify(productRepository).searchProducts(
            eq("iPhone"), isNull(), isNull(), isNull(), any(Pageable.class));
    }

    @Test
    void searchProducts_emptyResult_returnsEmptyPage() {
        when(productRepository.searchProducts(
            any(), any(), any(), any(), any(Pageable.class)
        )).thenReturn(new PageImpl<>(List.of()));

        ProductSearchRequest req = new ProductSearchRequest();
        req.setKeyword("NonExistentProduct");

        PageResult<ProductDTO> result = productService.searchProducts(req);

        assertThat(result.getTotalElements()).isZero();
        assertThat(result.getContent()).isEmpty();
    }

    @Test
    void searchProducts_withPriceRange_passesParamsToRepository() {
        when(productRepository.searchProducts(
            any(), any(), any(), any(), any(Pageable.class)
        )).thenReturn(new PageImpl<>(List.of()));

        ProductSearchRequest req = new ProductSearchRequest();
        req.setMinPrice(new BigDecimal("100"));
        req.setMaxPrice(new BigDecimal("500"));

        productService.searchProducts(req);

        verify(productRepository).searchProducts(
            isNull(),
            isNull(),
            eq(new BigDecimal("100")),
            eq(new BigDecimal("500")),
            any(Pageable.class)
        );
    }

    // ── getProductDetail ──────────────────────────────────────────────────────

    @Test
    void getProductDetail_success_returnsDetailWithListings() {
        Product p = buildProduct(1L, "canon-001", "iPhone 15 Pro", 10L);
        PlatformListing jd  = buildListing(1L, "canon-001", "jd",     "7999.00");
        PlatformListing pdd = buildListing(2L, "canon-001", "pdd",    "7799.00");

        when(productRepository.findById(1L)).thenReturn(Optional.of(p));
        when(listingRepository.findByCanonicalIdOrderByCurrentPriceAsc("canon-001"))
            .thenReturn(List.of(pdd, jd)); // sorted cheapest first

        ProductDetailDTO detail = productService.getProductDetail(1L);

        assertThat(detail.getProduct().getCanonicalId()).isEqualTo("canon-001");
        assertThat(detail.getListings()).hasSize(2);
        // first listing should be the cheaper one (pdd @ 7799)
        assertThat(detail.getListings().get(0).getPlatform()).isEqualTo("pdd");
        assertThat(detail.getListings().get(0).getCurrentPrice())
            .isEqualByComparingTo("7799.00");
    }

    @Test
    void getProductDetail_notFound_throwsIllegalArgumentException() {
        when(productRepository.findById(999L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> productService.getProductDetail(999L))
            .isInstanceOf(IllegalArgumentException.class)
            .hasMessageContaining("商品不存在");
    }

    @Test
    void getProductDetail_noListings_returnsEmptyListingsArray() {
        Product p = buildProduct(2L, "canon-002", "Samsung Galaxy S24", 10L);

        when(productRepository.findById(2L)).thenReturn(Optional.of(p));
        when(listingRepository.findByCanonicalIdOrderByCurrentPriceAsc("canon-002"))
            .thenReturn(List.of());

        ProductDetailDTO detail = productService.getProductDetail(2L);

        assertThat(detail.getProduct().getId()).isEqualTo(2L);
        assertThat(detail.getListings()).isEmpty();
    }

    // ── getPlatformComparison ─────────────────────────────────────────────────

    @Test
    void getPlatformComparison_success_returnsSortedListings() {
        PlatformListing jd      = buildListing(1L, "canon-001", "jd",      "7999.00");
        PlatformListing taobao  = buildListing(2L, "canon-001", "taobao",  "7899.00");
        PlatformListing pdd     = buildListing(3L, "canon-001", "pdd",     "7799.00");

        // Repository returns already sorted by currentPrice ASC
        when(listingRepository.findByCanonicalIdOrderByCurrentPriceAsc("canon-001"))
            .thenReturn(List.of(pdd, taobao, jd));

        List<PlatformListingDTO> listings = productService.getPlatformComparison("canon-001");

        assertThat(listings).hasSize(3);
        assertThat(listings.get(0).getPlatform()).isEqualTo("pdd");
        assertThat(listings.get(0).getCurrentPrice()).isEqualByComparingTo("7799.00");
        assertThat(listings.get(1).getPlatform()).isEqualTo("taobao");
        assertThat(listings.get(2).getPlatform()).isEqualTo("jd");
    }

    @Test
    void getPlatformComparison_notFound_throwsIllegalArgumentException() {
        when(listingRepository.findByCanonicalIdOrderByCurrentPriceAsc("nonexistent"))
            .thenReturn(List.of());

        assertThatThrownBy(() -> productService.getPlatformComparison("nonexistent"))
            .isInstanceOf(IllegalArgumentException.class)
            .hasMessageContaining("未找到该商品的平台报价");
    }

    // ── getCategories ─────────────────────────────────────────────────────────

    @Test
    void getCategories_buildsCategoryTree() {
        Category root  = buildCategory(1L, "手机数码", null);
        Category child = buildCategory(2L, "智能手机", 1L);

        when(categoryRepository.findByEnabledTrueOrderBySortOrderAsc())
            .thenReturn(List.of(root, child));

        List<CategoryDTO> tree = productService.getCategories();

        assertThat(tree).hasSize(1);
        assertThat(tree.get(0).getName()).isEqualTo("手机数码");
        assertThat(tree.get(0).getChildren()).hasSize(1);
        assertThat(tree.get(0).getChildren().get(0).getName()).isEqualTo("智能手机");
    }

    @Test
    void getCategories_emptyDatabase_returnsEmptyList() {
        when(categoryRepository.findByEnabledTrueOrderBySortOrderAsc())
            .thenReturn(List.of());

        List<CategoryDTO> tree = productService.getCategories();

        assertThat(tree).isEmpty();
    }
}
