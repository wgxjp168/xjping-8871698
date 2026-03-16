package com.ilbuy.contract.model.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "contract_signature")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ContractSignature {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "contract_id", nullable = false)
    private Long contractId;

    @Column(name = "signer_user_id", nullable = false)
    private Long signerUserId;

    @Column(name = "signer_role", nullable = false, length = 20)
    private String signerRole;

    @Column(name = "sign_method", nullable = false, length = 20)
    private String signMethod;

    @CreationTimestamp
    @Column(name = "signed_at", nullable = false, updatable = false)
    private LocalDateTime signedAt;

    @Column(name = "signature_image_url", length = 500)
    private String signatureImageUrl;
}
