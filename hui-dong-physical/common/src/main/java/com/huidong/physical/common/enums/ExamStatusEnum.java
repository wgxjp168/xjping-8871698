package com.huidong.physical.common.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

/**
 * 体检状态枚举
 */
@Getter
@AllArgsConstructor
public enum ExamStatusEnum {

    PENDING(0, "待体检"),
    IN_PROGRESS(1, "体检中"),
    SPECIMEN_COLLECTED(2, "标本已采集"),
    LAB_TESTING(3, "检验中"),
    COMPLETED(4, "已完成"),
    CANCELLED(5, "已取消");

    private final Integer code;
    private final String desc;

    public static ExamStatusEnum fromCode(Integer code) {
        for (ExamStatusEnum e : values()) {
            if (e.code.equals(code)) {
                return e;
            }
        }
        throw new IllegalArgumentException("未知体检状态: " + code);
    }
}
