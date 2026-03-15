package com.ilbuy.datasvc.repository.es;

import com.ilbuy.datasvc.model.document.ProductDocument;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.elasticsearch.repository.ElasticsearchRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface ProductEsRepository extends ElasticsearchRepository<ProductDocument, String> {

    Page<ProductDocument> findByPlatform(String platform, Pageable pageable);

    Page<ProductDocument> findByBrandNormalisedAndGrade(String brand, String grade, Pageable pageable);

    Page<ProductDocument> findByGradeAndInStockTrue(String grade, Pageable pageable);

    long countByPlatform(String platform);
}
