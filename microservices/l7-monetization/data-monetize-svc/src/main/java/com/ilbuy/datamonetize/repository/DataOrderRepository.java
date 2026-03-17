package com.ilbuy.datamonetize.repository;

import com.ilbuy.datamonetize.domain.DataOrder;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface DataOrderRepository extends JpaRepository<DataOrder, Long> {

    Optional<DataOrder> findByOrderNo(String orderNo);

    List<DataOrder> findByUserId(Long userId);

    List<DataOrder> findByCorpId(Long corpId);

    Optional<DataOrder> findByPaymentNo(String paymentNo);
}
