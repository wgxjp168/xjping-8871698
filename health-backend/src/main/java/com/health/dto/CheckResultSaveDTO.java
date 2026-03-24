package com.health.dto;

import lombok.Data;
import javax.validation.constraints.NotNull;
import java.time.LocalDateTime;

/**
 * 体检结果保存请求
 */
@Data
public class CheckResultSaveDTO {

    private Long id;

    @NotNull(message = "体检单ID不能为空")
    private Long orderId;

    @NotNull(message = "检查项ID不能为空")
    private Long itemId;

    private String value;

    private String unit;

    private String flag;

    private Long deviceId;

    private String dataSource;

    private String remark;

    private LocalDateTime checkTime;
}
