package com.ilbuy.datasvc.model.dto;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class SearchResponse {
    private long total;
    private int page;
    private int size;
    private long tookMs;
    private List<ProductSummaryDTO> items;
}
