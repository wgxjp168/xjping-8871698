package com.ilbuy.supplier.repository;

import com.ilbuy.supplier.model.entity.SupplierDocument;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface SupplierDocumentRepository extends JpaRepository<SupplierDocument, Long> {

    List<SupplierDocument> findBySupplierId(Long supplierId);

    Optional<SupplierDocument> findByIdAndSupplierId(Long id, Long supplierId);
}
