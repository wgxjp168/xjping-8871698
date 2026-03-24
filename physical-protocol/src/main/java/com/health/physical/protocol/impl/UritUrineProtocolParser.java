package com.health.physical.protocol.impl;

import com.health.physical.protocol.InstrumentProtocolParser;
import com.health.physical.protocol.dto.UrineDataPacket;
import lombok.extern.slf4j.Slf4j;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

/**
 * 优利特 Urit-500B / Urit-300 尿机串口协议解析器
 *
 * <p>优利特尿机通过串口（RS-232）或TCP输出如下格式的文本报文：
 * <pre>
 * H|\^&|||Urit-500B|||||||P|1|20240315120000
 * P|1||BARCODE001|||||||||||||||
 * O|1|BARCODE001||^^^LEU\^^^NIT\^^^PRO\^^^GLU|R||||||||||||
 * R|1|^^^LEU|2+|neg/±/1+/2+/3+|||N|||F|||20240315120000
 * R|2|^^^NIT|neg|||||||F|||20240315120000
 * ...
 * L|1|N
 * </pre>
 * 本解析器兼容ASTM E1381/E1394标准格式（LIS协议子集）。
 */
@Slf4j
public class UritUrineProtocolParser implements InstrumentProtocolParser<UrineDataPacket> {

    private static final DateTimeFormatter DT_FMT = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");

    /** Urit设备特征标识 */
    private static final String URIT_DEVICE_KEYWORD = "Urit";

    /** 各指标与字段名的映射 */
    private static final Map<String, String> ITEM_FIELD_MAP = new HashMap<>();

    static {
        ITEM_FIELD_MAP.put("LEU", "leu");
        ITEM_FIELD_MAP.put("NIT", "nit");
        ITEM_FIELD_MAP.put("PRO", "pro");
        ITEM_FIELD_MAP.put("GLU", "glu");
        ITEM_FIELD_MAP.put("KET", "ket");
        ITEM_FIELD_MAP.put("BIL", "bil");
        ITEM_FIELD_MAP.put("URO", "uro");
        ITEM_FIELD_MAP.put("ERY", "ery");
        ITEM_FIELD_MAP.put("BLD", "bld");
        ITEM_FIELD_MAP.put("VC",  "vc");
        ITEM_FIELD_MAP.put("MALB","malb");
        ITEM_FIELD_MAP.put("SG",  "specificGravity");
        ITEM_FIELD_MAP.put("PH",  "ph");
        ITEM_FIELD_MAP.put("COLOR", "color");
        ITEM_FIELD_MAP.put("CLARITY", "clarity");
    }

    @Override
    public boolean supports(String rawMessage) {
        return rawMessage != null && rawMessage.contains(URIT_DEVICE_KEYWORD);
    }

    @Override
    public UrineDataPacket parse(String rawMessage) {
        if (rawMessage == null || rawMessage.isBlank()) {
            return UrineDataPacket.error(rawMessage, "报文为空");
        }
        try {
            return doParseAstm(rawMessage);
        } catch (Exception e) {
            log.error("[UritParser] 解析失败: {}", e.getMessage());
            return UrineDataPacket.error(rawMessage, e.getMessage());
        }
    }

    private UrineDataPacket doParseAstm(String rawMessage) {
        UrineDataPacket packet = new UrineDataPacket();
        packet.setRawMessage(rawMessage);

        String[] lines = rawMessage.split("\r?\n");
        for (String line : lines) {
            line = line.trim();
            if (line.isEmpty()) continue;

            char recordType = line.charAt(0);
            String[] fields = line.split("\\|", -1);

            switch (recordType) {
                case 'H': parseHeader(fields, packet); break;
                case 'P': parsePatient(fields, packet); break;
                case 'R': parseResult(fields, packet);  break;
                default:  break;
            }
        }

        packet.setParseSuccess(true);
        return packet;
    }

    /**
     * H记录 - 报文头，包含设备信息和时间
     * H|\^&|||Urit-500B|||||||P|1|20240315120000
     */
    private void parseHeader(String[] fields, UrineDataPacket packet) {
        // fields[4] = 设备型号
        if (fields.length > 4 && !fields[4].isBlank()) {
            packet.setDeviceSn(fields[4]);
        }
        // fields[13] = 报文时间
        if (fields.length > 13 && fields[13].length() >= 14) {
            try {
                packet.setExamTime(LocalDateTime.parse(fields[13].substring(0, 14), DT_FMT));
            } catch (Exception ignored) {
                packet.setExamTime(LocalDateTime.now());
            }
        }
    }

    /**
     * P记录 - 患者/标本信息
     * P|1||BARCODE001
     */
    private void parsePatient(String[] fields, UrineDataPacket packet) {
        if (fields.length > 3 && !fields[3].isBlank()) {
            packet.setBarcode(fields[3]);
        }
    }

    /**
     * R记录 - 检验结果
     * R|1|^^^LEU|2+|neg/±/1+/2+/3+|||N|||F|||20240315120000
     * fields[2] = ^^^ITEM_CODE
     * fields[3] = 结果值
     * fields[6] = 异常标志 (H/L/N/C)
     */
    private void parseResult(String[] fields, UrineDataPacket packet) {
        if (fields.length < 4) return;

        String itemRaw = fields[2]; // ^^^LEU
        String itemCode = itemRaw.replaceAll("\\^+", "").trim().toUpperCase();
        String resultVal = fields[3].trim();

        // 异常标志在 fields[6]
        String abnFlag = (fields.length > 6) ? fields[6].trim() : "";

        setItemValue(packet, itemCode, resultVal);
        log.debug("[UritParser] itemCode={} value={} flag={}", itemCode, resultVal, abnFlag);
    }

    /** 将解析出的指标值设置到对应字段 */
    private void setItemValue(UrineDataPacket packet, String itemCode, String value) {
        switch (itemCode) {
            case "LEU":     packet.setLeu(value);             break;
            case "NIT":     packet.setNit(value);             break;
            case "PRO":     packet.setPro(value);             break;
            case "GLU":     packet.setGlu(value);             break;
            case "KET":     packet.setKet(value);             break;
            case "BIL":     packet.setBil(value);             break;
            case "URO":     packet.setUro(value);             break;
            case "ERY":     packet.setEry(value);             break;
            case "BLD":     packet.setBld(value);             break;
            case "VC":      packet.setVc(value);              break;
            case "MALB":    packet.setMalb(value);            break;
            case "SG":      packet.setSpecificGravity(value); break;
            case "PH":      packet.setPh(value);              break;
            case "COLOR":   packet.setColor(value);           break;
            case "CLARITY": packet.setClarity(value);         break;
            default:
                log.debug("[UritParser] 未识别指标: {}", itemCode);
        }
    }
}
