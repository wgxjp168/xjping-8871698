package com.ilbuy.reportgen.model.dto;

import lombok.Builder;
import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
@Builder
public class ChartData {
    private String chartId;
    private String type;          // bar | line | pie | radar | scatter
    private String title;
    private List<String> labels;
    private List<Map<String, Object>> datasets;
}
