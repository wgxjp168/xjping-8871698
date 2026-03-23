package com.huidong.physical.common.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

/**
 * 同步状态枚举（上报县域公卫平台）
 */
@Getter
@AllArgsConstructor
public enum SyncStatusEnum {

    PENDING(0, "待上报"),
    SUCCESS(1, "上报成功"),
    FAILED(2, "上报失败"),
    RETRYING(3, "重试中"),
    EXHAUSTED(4, "重试耗尽");

    private final Integer code;
    private final String desc;
}
