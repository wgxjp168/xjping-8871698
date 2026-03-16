package com.ilbuy.reportgen.model.dto;

import com.ilbuy.reportgen.model.enums.ClientType;
import com.ilbuy.reportgen.model.enums.JobStatus;
import com.ilbuy.reportgen.model.enums.ReportBusinessType;
import lombok.Builder;
import lombok.Data;

import java.time.OffsetDateTime;

@Data
@Builder
public class JobStatusDTO {
    private Long id;
    private String jobNo;
    private String l5ReportNo;
    private Long userId;
    private ClientType clientType;
    private ReportBusinessType businessType;
    private JobStatus status;
    private Integer retryCount;
    private String errorMessage;
    private Long formatJobId;
    private OffsetDateTime startedAt;
    private OffsetDateTime completedAt;
    private OffsetDateTime createdAt;
}
