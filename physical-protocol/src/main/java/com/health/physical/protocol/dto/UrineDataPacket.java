package com.health.physical.protocol.dto;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * 优利特尿机数据包 - 解析后的标准结构
 * 对应 Urit-500B / Urit-300 等型号的串口/TCP输出
 */
@Data
public class UrineDataPacket {

    /** 设备序列号（SN） */
    private String deviceSn;

    /** 标本条码 */
    private String barcode;

    /** 检测时间（设备本地时间） */
    private LocalDateTime examTime;

    // ===== 物理性状 =====
    private String color;         // 颜色（黄色/深黄/淡黄）
    private String clarity;       // 透明度（清晰/浑浊）
    private String specificGravity; // 比重（1.000~1.030）
    private String ph;            // pH（4.5~9.0）

    // ===== 化学项目（干化学法） =====
    /** 白细胞 LEU（neg/±/1+/2+/3+） */
    private String leu;

    /** 亚硝酸盐 NIT（neg/pos） */
    private String nit;

    /** 尿蛋白 PRO（neg/±/1+/2+/3+） */
    private String pro;

    /** 葡萄糖 GLU（neg/±/1+/2+/3+） */
    private String glu;

    /** 酮体 KET（neg/±/1+/2+/3+） */
    private String ket;

    /** 胆红素 BIL（neg/1+/2+/3+） */
    private String bil;

    /** 尿胆原 URO（neg/norm/1+/2+/3+） */
    private String uro;

    /** 红细胞 ERY（neg/±/1+/2+/3+） */
    private String ery;

    /** 隐血 BLD（neg/±/1+/2+/3+） */
    private String bld;

    /** 维生素C VC（neg/1+/2+） */
    private String vc;

    /** 微白蛋白 mALB（neg/±/1+/2+/3+） */
    private String malb;

    /** 原始报文（用于问题排查） */
    private String rawMessage;

    /** 解析是否成功 */
    private boolean parseSuccess = true;

    /** 解析错误信息 */
    private String parseError;

    public static UrineDataPacket error(String rawMessage, String errorMsg) {
        UrineDataPacket pkt = new UrineDataPacket();
        pkt.setRawMessage(rawMessage);
        pkt.setParseSuccess(false);
        pkt.setParseError(errorMsg);
        return pkt;
    }
}
