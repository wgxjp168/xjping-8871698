package com.ilbuy.supplier.repository;

import com.ilbuy.supplier.model.entity.RfqQuote;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface RfqQuoteRepository extends JpaRepository<RfqQuote, Long> {

    Optional<RfqQuote> findByRfqId(Long rfqId);
}
