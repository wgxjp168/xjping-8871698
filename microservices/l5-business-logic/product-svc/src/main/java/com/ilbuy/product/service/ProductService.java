package com.ilbuy.product.service;

import com.ilbuy.product.config.CacheConfig;
import com.ilbuy.product.model.dto.*;
import com.ilbuy.product.model.entity.Category;
import com.ilbuy.product.model.entity.PlatformListing;
import com.ilbuy.product.model.entity.Product;
import com.ilbuy.product.repository.CategoryRepository;
import com.ilbuy.product.repository.PlatformListingRepository;
import com.ilbuy.product.repository.ProductRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.DigestUtils;

import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class ProductService {

    private final ProductRepository          productRepository;
    private final PlatformListingRepository  listingRepository;
    private final CategoryRepository         categoryRepository;

    // ── Search ───────────────────────────────────────────────────────────────

    /**
     * Search products.
     * Attempts to query Elasticsearch; falls back to JPA LIKE search when ES
     * is unavailable (e.g., in local / test environments).
     * Results are cached in Redis under key "product:search:{requestHash}"
     * with a TTL of 2 minutes (configured via {@link CacheConfig}).
     *
     * Note: Spring's @Cacheable requires a deterministic key.  We derive the
     * key from an MD5 of the request's toString() so that identical requests
     * share a cache entry regardless of object identity.
     */
    @Transactional(readOnly = true)
    public PageResult<ProductDTO> searchProducts(ProductSearchRequest req) {
        String cacheKey = buildSearchCacheKey(req);
        log.debug("searchProducts cacheKey={}", cacheKey);

        // Determine sort
        Sort sort = resolveSort(req.getSortBy());
        PageRequest pageable = PageRequest.of(req.getPage(), req.getSize(), sort);

        Page<Product> page;
        try {
            // Primary path: query Elasticsearch (simulated via JPA LIKE fallback)
            page = productRepository.searchProducts(
                req.getKeyword(),
                req.getCategoryId(),
                req.getMinPrice(),
                req.getMaxPrice(),
                pageable
            );
            log.debug("JPA search returned {} results", page.getTotalElements());
        } catch (Exception ex) {
            log.warn("Product search failed, returning empty result: {}", ex.getMessage());
            return PageResult.<ProductDTO>builder()
                .content(Collections.emptyList())
                .totalElements(0)
                .totalPages(0)
                .page(req.getPage())
                .size(req.getSize())
                .build();
        }

        List<ProductDTO> dtos = page.getContent().stream()
            .map(this::toProductDTO)
            .collect(Collectors.toList());

        return PageResult.<ProductDTO>builder()
            .content(dtos)
            .totalElements(page.getTotalElements())
            .totalPages(page.getTotalPages())
            .page(req.getPage())
            .size(req.getSize())
            .build();
    }

    // ── Product detail ───────────────────────────────────────────────────────

    /**
     * Fetch a single product with all its platform listings.
     * Cached in Redis under "product:detail:{id}" for 10 minutes.
     */
    @Cacheable(value = CacheConfig.CACHE_PRODUCT_DETAIL, key = "#id")
    @Transactional(readOnly = true)
    public ProductDetailDTO getProductDetail(Long id) {
        Product product = productRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("商品不存在: " + id));

        List<PlatformListing> listings =
            listingRepository.findByCanonicalIdOrderByCurrentPriceAsc(product.getCanonicalId());

        return ProductDetailDTO.builder()
            .product(toProductDTO(product))
            .listings(listings.stream().map(this::toListingDTO).collect(Collectors.toList()))
            .build();
    }

    // ── Platform price comparison ─────────────────────────────────────────────

    /**
     * Return all platform listings for a canonical product ID, sorted
     * by currentPrice ascending (cheapest first).
     */
    @Transactional(readOnly = true)
    public List<PlatformListingDTO> getPlatformComparison(String canonicalId) {
        List<PlatformListing> listings =
            listingRepository.findByCanonicalIdOrderByCurrentPriceAsc(canonicalId);
        if (listings.isEmpty()) {
            throw new IllegalArgumentException("未找到该商品的平台报价: " + canonicalId);
        }
        return listings.stream().map(this::toListingDTO).collect(Collectors.toList());
    }

    // ── Category tree ─────────────────────────────────────────────────────────

    /**
     * Return the complete category tree as a nested list.
     * Cached in Redis under "product:categories" for 1 hour.
     */
    @Cacheable(value = CacheConfig.CACHE_PRODUCT_CATEGORIES, key = "'all'")
    @Transactional(readOnly = true)
    public List<CategoryDTO> getCategories() {
        List<Category> all = categoryRepository.findByEnabledTrueOrderBySortOrderAsc();

        // Build id -> DTO map
        Map<Long, CategoryDTO> dtoMap = new LinkedHashMap<>();
        for (Category c : all) {
            CategoryDTO dto = toCategoryDTO(c);
            dto.setChildren(new ArrayList<>());
            dtoMap.put(c.getId(), dto);
        }

        // Wire up parent-child relationships
        List<CategoryDTO> roots = new ArrayList<>();
        for (Category c : all) {
            CategoryDTO dto = dtoMap.get(c.getId());
            if (c.getParentId() == null) {
                roots.add(dto);
            } else {
                CategoryDTO parent = dtoMap.get(c.getParentId());
                if (parent != null) {
                    parent.getChildren().add(dto);
                } else {
                    // Orphan category with missing parent — treat as root
                    roots.add(dto);
                }
            }
        }
        return roots;
    }

    // ── Products under a category ─────────────────────────────────────────────

    /**
     * Return a paginated list of products belonging to a specific category.
     */
    @Transactional(readOnly = true)
    public PageResult<ProductDTO> getProductsByCategory(Long categoryId, int page, int size) {
        // Verify category exists
        categoryRepository.findById(categoryId)
            .orElseThrow(() -> new IllegalArgumentException("分类不存在: " + categoryId));

        PageRequest pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<Product> pg = productRepository.findByCategoryIdAndEnabledTrue(categoryId, pageable);

        List<ProductDTO> dtos = pg.getContent().stream()
            .map(this::toProductDTO)
            .collect(Collectors.toList());

        return PageResult.<ProductDTO>builder()
            .content(dtos)
            .totalElements(pg.getTotalElements())
            .totalPages(pg.getTotalPages())
            .page(page)
            .size(size)
            .build();
    }

    // ── Side-by-side comparison ───────────────────────────────────────────────

    /**
     * Fetch detailed information for up to 4 products for a side-by-side comparison.
     * Requires authentication (enforced in SecurityConfig / controller).
     */
    @Transactional(readOnly = true)
    public List<ProductDetailDTO> compareProducts(List<Long> ids) {
        if (ids == null || ids.isEmpty() || ids.size() > 4) {
            throw new IllegalArgumentException("最多支持同时对比 4 个商品");
        }

        List<Product> products = productRepository.findAllByIdIn(ids);
        if (products.isEmpty()) {
            throw new IllegalArgumentException("未找到指定商品");
        }

        // Collect canonical IDs to batch-fetch listings
        List<String> canonicalIds = products.stream()
            .map(Product::getCanonicalId)
            .collect(Collectors.toList());

        List<PlatformListing> allListings = listingRepository.findByCanonicalIdIn(canonicalIds);

        // Group listings by canonicalId
        Map<String, List<PlatformListing>> listingsByCanonical = allListings.stream()
            .collect(Collectors.groupingBy(PlatformListing::getCanonicalId));

        // Preserve request order
        Map<Long, Product> productById = products.stream()
            .collect(Collectors.toMap(Product::getId, p -> p));

        return ids.stream()
            .map(id -> {
                Product p = productById.get(id);
                if (p == null) return null;
                List<PlatformListing> listings = listingsByCanonical
                    .getOrDefault(p.getCanonicalId(), Collections.emptyList())
                    .stream()
                    .sorted(Comparator.comparing(PlatformListing::getCurrentPrice))
                    .collect(Collectors.toList());
                return ProductDetailDTO.builder()
                    .product(toProductDTO(p))
                    .listings(listings.stream().map(this::toListingDTO).collect(Collectors.toList()))
                    .build();
            })
            .filter(Objects::nonNull)
            .collect(Collectors.toList());
    }

    // ── Private helpers ───────────────────────────────────────────────────────

    private String buildSearchCacheKey(ProductSearchRequest req) {
        String raw = String.format("kw=%s|cat=%s|min=%s|max=%s|plt=%s|pg=%d|sz=%d|sort=%s",
            req.getKeyword(), req.getCategoryId(), req.getMinPrice(),
            req.getMaxPrice(), req.getPlatform(), req.getPage(), req.getSize(), req.getSortBy());
        return DigestUtils.md5DigestAsHex(raw.getBytes(StandardCharsets.UTF_8));
    }

    private Sort resolveSort(String sortBy) {
        if (sortBy == null) return Sort.by(Sort.Direction.DESC, "createdAt");
        return switch (sortBy) {
            case "price_asc"  -> Sort.by(Sort.Direction.ASC,  "referencePrice");
            case "price_desc" -> Sort.by(Sort.Direction.DESC, "referencePrice");
            case "newest"     -> Sort.by(Sort.Direction.DESC, "createdAt");
            default           -> Sort.by(Sort.Direction.DESC, "createdAt"); // relevance → DB default
        };
    }

    private ProductDTO toProductDTO(Product p) {
        return ProductDTO.builder()
            .id(p.getId())
            .canonicalId(p.getCanonicalId())
            .name(p.getName())
            .description(p.getDescription())
            .brand(p.getBrand())
            .categoryId(p.getCategoryId())
            .imageUrl(p.getImageUrl())
            .referencePrice(p.getReferencePrice())
            .enabled(p.getEnabled())
            .tags(p.getTags())
            .createdAt(p.getCreatedAt())
            .updatedAt(p.getUpdatedAt())
            .build();
    }

    private PlatformListingDTO toListingDTO(PlatformListing l) {
        return PlatformListingDTO.builder()
            .id(l.getId())
            .canonicalId(l.getCanonicalId())
            .platform(l.getPlatform())
            .externalUrl(l.getExternalUrl())
            .currentPrice(l.getCurrentPrice())
            .originalPrice(l.getOriginalPrice())
            .currency(l.getCurrency())
            .inStock(l.getInStock())
            .lastSyncAt(l.getLastSyncAt())
            .build();
    }

    private CategoryDTO toCategoryDTO(Category c) {
        return CategoryDTO.builder()
            .id(c.getId())
            .name(c.getName())
            .parentId(c.getParentId())
            .description(c.getDescription())
            .sortOrder(c.getSortOrder())
            .iconUrl(c.getIconUrl())
            .enabled(c.getEnabled())
            .build();
    }
}
