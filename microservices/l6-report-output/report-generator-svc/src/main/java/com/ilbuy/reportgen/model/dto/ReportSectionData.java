package com.ilbuy.reportgen.model.dto;

import lombok.Builder;
import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
@Builder
public class ReportSectionData {
    private String sectionKey;
    private String title;
    private Map<String, Object> content;
    private List<ChartData> charts;
    private int orderIndex;
}
