package com.ilbuy.contract.repository;

import com.ilbuy.contract.model.entity.Contract;
import com.ilbuy.contract.model.enums.ContractStatus;
import com.ilbuy.contract.model.enums.ContractType;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface ContractRepository extends JpaRepository<Contract, Long> {

    Optional<Contract> findByContractNo(String contractNo);

    @Query("SELECT c FROM Contract c WHERE c.buyerUserId = :userId AND " +
           "(:status IS NULL OR c.status = :status) AND " +
           "(:type IS NULL OR c.type = :type)")
    Page<Contract> findByUserIdAndFilters(
        @Param("userId") Long userId,
        @Param("status") ContractStatus status,
        @Param("type") ContractType type,
        Pageable pageable
    );
}
