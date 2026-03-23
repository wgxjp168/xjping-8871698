package com.huidong.physical.common.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

/**
 * 设备类型枚举
 */
@Getter
@AllArgsConstructor
public enum DeviceTypeEnum {

    URINE_ANALYZER("URINE", "尿机（优利特）"),
    BIOCHEMISTRY("BIO", "生化仪（迈瑞）"),
    BLOOD_ROUTINE("CBC", "血常规（万瑞）"),
    HBA1C("HBA1C", "糖化血红蛋白（万瑞）"),
    BARCODE_SCANNER("SCANNER", "扫码枪"),
    TABLET("TABLET", "平板电脑（已建）"),
    LAPTOP("LAPTOP", "手提电脑（下乡尿机专用）");

    private final String code;
    private final String desc;
}
