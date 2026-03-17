package com.ilbuy.datamonetize.repository;

import com.ilbuy.datamonetize.domain.DataProduct;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface DataProductRepository extends JpaRepository<DataProduct, Long> {

    Optional<DataProduct> findByProductCodeAndEnabled(String productCode, Boolean enabled);

    List<DataProduct> findAllByEnabledTrue();
}
