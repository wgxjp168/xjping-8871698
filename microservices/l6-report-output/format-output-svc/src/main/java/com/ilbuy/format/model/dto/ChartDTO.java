package com.ilbuy.format.model.dto;

import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
public class ChartDTO {
    private String chartId;
    private String type;
    private String title;
    private List<String> labels;
    private List<Map<String, Object>> datasets;
}
