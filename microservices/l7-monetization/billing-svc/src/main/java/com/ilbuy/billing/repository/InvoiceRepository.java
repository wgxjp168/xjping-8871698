package com.ilbuy.billing.repository;

import com.ilbuy.billing.domain.Invoice;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface InvoiceRepository extends JpaRepository<Invoice, Long> {

    Optional<Invoice> findByInvoiceNo(String invoiceNo);

    Optional<Invoice> findByOrderNo(String orderNo);

    List<Invoice> findByUserId(Long userId);

    List<Invoice> findByCorpId(Long corpId);
}
