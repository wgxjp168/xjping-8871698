package com.ilbuy.format.model.dto;

import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
public class SectionDTO {
    private String sectionKey;
    private String title;
    private Map<String, Object> content;
    private List<ChartDTO> charts;
    private int orderIndex;
}
