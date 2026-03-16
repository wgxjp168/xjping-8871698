package com.ilbuy.contract.repository;

import com.ilbuy.contract.model.entity.Invoice;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface InvoiceRepository extends JpaRepository<Invoice, Long> {

    Optional<Invoice> findByInvoiceNo(String invoiceNo);

    Page<Invoice> findByUserId(Long userId, Pageable pageable);

    boolean existsByInvoiceNo(String invoiceNo);
}
