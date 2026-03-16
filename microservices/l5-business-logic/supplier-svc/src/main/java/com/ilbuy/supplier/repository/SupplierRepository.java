package com.ilbuy.supplier.repository;

import com.ilbuy.supplier.model.entity.Supplier;
import com.ilbuy.supplier.model.enums.SupplierStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface SupplierRepository extends JpaRepository<Supplier, Long> {

    Optional<Supplier> findBySupplierNo(String supplierNo);

    boolean existsByBusinessLicense(String businessLicense);

    @Query("SELECT s FROM Supplier s WHERE " +
           "(:status IS NULL OR s.status = :status) AND " +
           "(:keyword IS NULL OR :keyword = '' OR " +
           "LOWER(s.companyName) LIKE LOWER(CONCAT('%', :keyword, '%')) OR " +
           "LOWER(s.contactName) LIKE LOWER(CONCAT('%', :keyword, '%')))")
    Page<Supplier> findByStatusAndKeyword(
        @Param("status") SupplierStatus status,
        @Param("keyword") String keyword,
        Pageable pageable
    );
}
