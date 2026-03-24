package com.health.vo;

import lombok.Data;
import java.time.LocalDateTime;

/**
 * 体检结果视图对象
 */
@Data
public class CheckResultVO {

    private Long id;
    private Long orderId;
    private Long itemId;
    private String itemName;
    private String category;
    private String value;
    private String unit;
    private String normalRange;
    private String flag;
    private Long deviceId;
    private String deviceName;
    private String dataSource;
    private Long doctorId;
    private String doctorName;
    private String remark;
    private LocalDateTime checkTime;
}
