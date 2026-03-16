package com.ilbuy.supplier.model.dto;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class SupplierDetailDTO {

    private SupplierDTO supplier;
    private List<SupplierDocumentDTO> documents;
    private List<CooperationScoreDTO> scores;
}
