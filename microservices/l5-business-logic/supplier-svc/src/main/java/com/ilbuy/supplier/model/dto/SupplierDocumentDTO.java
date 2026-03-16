package com.ilbuy.supplier.model.dto;

import com.ilbuy.supplier.model.enums.DocumentType;
import lombok.Builder;
import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@Builder
public class SupplierDocumentDTO {

    private Long id;
    private Long supplierId;
    private DocumentType docType;
    private String docName;
    private String fileUrl;
    private LocalDate expiresAt;
    private LocalDateTime uploadedAt;
}
