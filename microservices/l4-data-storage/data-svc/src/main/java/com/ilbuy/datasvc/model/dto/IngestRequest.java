package com.ilbuy.datasvc.model.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.util.List;

/**
 * L3 ETL 服务推送的批量入库请求
 * 对应 etl-svc POST /etl/process 的输出结构
 */
@Data
public class IngestRequest {

    @NotBlank
    @JsonProperty("job_id")
    private String jobId;

    @NotBlank
    @JsonProperty("session_id")
    private String sessionId;

    @NotEmpty
    @Valid
    private List<ProductIngestDTO> products;
}
