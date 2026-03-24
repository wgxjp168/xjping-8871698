package com.health.physical.protocol.impl;

import com.health.physical.protocol.InstrumentProtocolParser;
import com.health.physical.protocol.dto.LabDataItem;
import lombok.extern.slf4j.Slf4j;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

/**
 * ASTM E1381/HL7 2.x 检验仪器协议解析器
 *
 * <p>适用于生化分析仪（迈瑞BS-380/BS-800、罗氏Cobas等）、
 * 血常规仪（迈瑞BC-5130）、糖化仪（普利生HLC-723）等使用ASTM/LIS接口的设备。
 *
 * <p>报文格式示例（ASTM E1394）：
 * <pre>
 * H|\^&|||BS-380|||||||P|1|20240315120000
 * P|1||BARCODE001
 * O|1|BARCODE001||^^^GLU\^^^CHOL\^^^TG|R||||||||||||
 * R|1|^^^GLU|5.3|mmol/L|3.9^6.1|N|||F|||20240315120000
 * R|2|^^^CHOL|4.8|mmol/L|3.1^5.7|N|||F|||20240315120000
 * R|3|^^^TG|1.7|mmol/L|0.4^1.7|N|||F|||20240315120000
 * L|1|N
 * </pre>
 */
@Slf4j
public class Hl7AstmLabProtocolParser implements InstrumentProtocolParser<LabDataItem> {

    private static final DateTimeFormatter DT_FMT = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");

    @Override
    public boolean supports(String rawMessage) {
        // ASTM报文以 H| 开头，且不包含 Urit 关键字
        return rawMessage != null
                && (rawMessage.startsWith("H|") || rawMessage.contains("\nH|"))
                && !rawMessage.contains("Urit");
    }

    @Override
    public LabDataItem parse(String rawMessage) {
        if (rawMessage == null || rawMessage.isBlank()) {
            return LabDataItem.error(rawMessage, "报文为空");
        }
        try {
            return doParseAstm(rawMessage);
        } catch (Exception e) {
            log.error("[HL7Parser] 解析失败: {}", e.getMessage());
            return LabDataItem.error(rawMessage, e.getMessage());
        }
    }

    private LabDataItem doParseAstm(String rawMessage) {
        LabDataItem item = new LabDataItem();
        item.setRawMessage(rawMessage);

        List<LabDataItem.ResultItem> resultItems = new ArrayList<>();
        String[] lines = rawMessage.split("\r?\n");

        for (String line : lines) {
            line = line.trim();
            if (line.isEmpty()) continue;

            char recordType = line.charAt(0);
            String[] fields = line.split("\\|", -1);

            switch (recordType) {
                case 'H': parseHeader(fields, item);        break;
                case 'P': parsePatient(fields, item);       break;
                case 'R': parseResult(fields, resultItems); break;
                default:  break;
            }
        }

        item.setResults(resultItems);
        item.setParseSuccess(true);
        return item;
    }

    /**
     * H记录 - 设备信息
     * H|\^&|||BS-380|||||||P|1|20240315120000
     */
    private void parseHeader(String[] fields, LabDataItem item) {
        if (fields.length > 4 && !fields[4].isBlank()) {
            item.setDeviceModel(fields[4]);
            item.setDeviceSn(fields[4]);
        }
        if (fields.length > 13 && fields[13].length() >= 14) {
            try {
                item.setExamTime(LocalDateTime.parse(fields[13].substring(0, 14), DT_FMT));
            } catch (Exception ignored) {
                item.setExamTime(LocalDateTime.now());
            }
        }
    }

    /**
     * P记录 - 标本/患者
     */
    private void parsePatient(String[] fields, LabDataItem item) {
        if (fields.length > 3 && !fields[3].isBlank()) {
            item.setBarcode(fields[3]);
            item.setPatientId(fields[3]);
        }
    }

    /**
     * R记录 - 单个检验结果
     * R|1|^^^GLU|5.3|mmol/L|3.9^6.1|N|||F|||20240315120000
     * fields[2] = ^^^ITEM_CODE
     * fields[3] = 结果值
     * fields[4] = 单位
     * fields[5] = 参考范围 low^high
     * fields[6] = 异常标志
     */
    private void parseResult(String[] fields, List<LabDataItem.ResultItem> results) {
        if (fields.length < 4) return;

        String itemRaw = fields[2];
        String itemCode = itemRaw.replaceAll("\\^+", "").trim().toUpperCase();
        String resultVal = fields.length > 3 ? fields[3].trim() : "";
        String unit = fields.length > 4 ? fields[4].trim() : "";
        String refRange = fields.length > 5 ? fields[5].trim() : "";
        String abnFlag = fields.length > 6 ? fields[6].trim() : "N";

        LabDataItem.ResultItem ri = new LabDataItem.ResultItem();
        ri.setItemCode(itemCode);
        ri.setItemName(itemCode);
        ri.setResultValue(resultVal);
        ri.setUnit(unit);
        ri.setAbnormalFlag(mapAbnFlag(abnFlag));

        // 解析结果数值
        try {
            ri.setResultNum(new BigDecimal(resultVal));
        } catch (NumberFormatException ignored) {
            // 非数值型结果（如 neg/1+/2+）无需设置数值
        }

        // 解析参考范围 low^high
        if (refRange.contains("^")) {
            String[] parts = refRange.split("\\^");
            try { ri.setRefLow(new BigDecimal(parts[0].trim())); } catch (Exception ignored) {}
            if (parts.length > 1) {
                try { ri.setRefHigh(new BigDecimal(parts[1].trim())); } catch (Exception ignored) {}
            }
        }

        results.add(ri);
        log.debug("[HL7Parser] itemCode={} value={} unit={} flag={}", itemCode, resultVal, unit, abnFlag);
    }

    /** ASTM异常标志映射到系统标志（N/L/H/C） */
    private String mapAbnFlag(String astmFlag) {
        if (astmFlag == null || astmFlag.isBlank()) return "N";
        switch (astmFlag.toUpperCase()) {
            case "H":  return "H";
            case "HH": return "C";
            case "L":  return "L";
            case "LL": return "C";
            case "A":  return "H";
            case "N":
            default:   return "N";
        }
    }
}
