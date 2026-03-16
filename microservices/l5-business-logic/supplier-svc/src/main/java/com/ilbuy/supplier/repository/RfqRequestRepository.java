package com.ilbuy.supplier.repository;

import com.ilbuy.supplier.model.entity.RfqRequest;
import com.ilbuy.supplier.model.enums.RfqStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface RfqRequestRepository extends JpaRepository<RfqRequest, Long> {

    Page<RfqRequest> findByBuyerUserId(Long buyerUserId, Pageable pageable);

    Page<RfqRequest> findBySupplierNo(String supplierNo, Pageable pageable);

    Optional<RfqRequest> findByRfqNo(String rfqNo);

    Page<RfqRequest> findByBuyerUserIdAndStatus(Long buyerUserId, RfqStatus status, Pageable pageable);

    Page<RfqRequest> findBySupplierNoAndStatus(String supplierNo, RfqStatus status, Pageable pageable);
}
