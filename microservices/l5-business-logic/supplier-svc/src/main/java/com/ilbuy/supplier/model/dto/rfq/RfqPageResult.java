package com.ilbuy.supplier.model.dto.rfq;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RfqPageResult {

    private List<RfqRequestDTO> content;
    private int page;
    private int size;
    private long totalElements;
    private int totalPages;
}
