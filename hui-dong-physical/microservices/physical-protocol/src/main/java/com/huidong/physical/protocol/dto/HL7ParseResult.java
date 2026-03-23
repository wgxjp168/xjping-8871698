package com.huidong.physical.protocol.dto;

import lombok.Data;

import java.util.List;

/**
 * HL7解析结果
 */
@Data
public class HL7ParseResult {

    /** 发送应用（设备标识） */
    private String sendingApp;

    /** 报文时间 */
    private String messageDateTime;

    /** 患者ID（对应扫码条码号或居民编码） */
    private String patientId;

    /** 患者姓名 */
    private String patientName;

    /** 检验项目列表 */
    private List<LabItemResult> items;

    /** 原始HL7报文 */
    private String rawMessage;
}
