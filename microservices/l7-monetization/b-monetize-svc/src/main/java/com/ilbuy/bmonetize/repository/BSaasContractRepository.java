package com.ilbuy.bmonetize.repository;

import com.ilbuy.bmonetize.domain.BSaasContract;
import com.ilbuy.bmonetize.domain.BSaasContract.ContractStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.*;

public interface BSaasContractRepository extends JpaRepository<BSaasContract, Long> {
    Optional<BSaasContract> findByContractNo(String contractNo);
    Optional<BSaasContract> findByCorpIdAndStatus(Long corpId, ContractStatus status);
    List<BSaasContract> findByCorpId(Long corpId);
}
