package com.ilbuy.contract.repository;

import com.ilbuy.contract.model.entity.ContractSignature;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ContractSignatureRepository extends JpaRepository<ContractSignature, Long> {

    List<ContractSignature> findByContractId(Long contractId);

    Optional<ContractSignature> findByContractIdAndSignerRole(Long contractId, String signerRole);

    boolean existsByContractIdAndSignerRole(Long contractId, String signerRole);
}
