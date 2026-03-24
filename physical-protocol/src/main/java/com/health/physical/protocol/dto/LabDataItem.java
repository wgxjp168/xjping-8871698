package com.health.physical.protocol.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * 检验仪器数据包（ASTM/HL7解析结果）
 * 适用于生化仪、血常规仪、糖化仪等
 */
@Data
public class LabDataItem {

    /** 设备序列号 */
    private String deviceSn;

    /** 设备型号 */
    private String deviceModel;

    /** 标本条码 */
    private String barcode;

    /** 项目编码（BIOCHEM/CBC/HBA1C） */
    private String projectCode;

    /** 患者ID（若设备传输） */
    private String patientId;

    /** 检验时间 */
    private LocalDateTime examTime;

    /** 检验结果项列表 */
    private List<ResultItem> results = new ArrayList<>();

    /** 原始报文 */
    private String rawMessage;

    /** 是否解析成功 */
    private boolean parseSuccess = true;

    /** 解析错误信息 */
    private String parseError;

    @Data
    public static class ResultItem {
        /** 指标编码（如 GLU、CHOL） */
        private String itemCode;
        /** 指标名称 */
        private String itemName;
        /** 结果文本值 */
        private String resultValue;
        /** 结果数值 */
        private BigDecimal resultNum;
        /** 单位 */
        private String unit;
        /** 参考范围下限 */
        private BigDecimal refLow;
        /** 参考范围上限 */
        private BigDecimal refHigh;
        /** 异常标志：N/L/H/C */
        private String abnormalFlag;
    }

    public static LabDataItem error(String rawMessage, String errorMsg) {
        LabDataItem item = new LabDataItem();
        item.setRawMessage(rawMessage);
        item.setParseSuccess(false);
        item.setParseError(errorMsg);
        return item;
    }
}
