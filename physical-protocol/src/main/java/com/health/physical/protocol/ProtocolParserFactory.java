package com.health.physical.protocol;

import com.health.physical.protocol.dto.LabDataItem;
import com.health.physical.protocol.dto.UrineDataPacket;
import com.health.physical.protocol.impl.Hl7AstmLabProtocolParser;
import com.health.physical.protocol.impl.UritUrineProtocolParser;
import lombok.extern.slf4j.Slf4j;

/**
 * 协议解析器工厂
 * 根据报文特征自动选择合适的解析器
 */
@Slf4j
public class ProtocolParserFactory {

    private static final UritUrineProtocolParser URIT_PARSER = new UritUrineProtocolParser();
    private static final Hl7AstmLabProtocolParser HL7_PARSER = new Hl7AstmLabProtocolParser();

    private ProtocolParserFactory() {}

    /**
     * 解析尿机报文（自动识别设备）
     */
    public static UrineDataPacket parseUrine(String rawMessage) {
        if (URIT_PARSER.supports(rawMessage)) {
            return URIT_PARSER.parse(rawMessage);
        }
        log.warn("[ProtocolFactory] 无匹配的尿机解析器，使用默认解析器");
        return URIT_PARSER.parse(rawMessage);
    }

    /**
     * 解析检验仪器报文（ASTM/HL7，适用于生化/血常规/糖化）
     */
    public static LabDataItem parseLab(String rawMessage) {
        if (HL7_PARSER.supports(rawMessage)) {
            return HL7_PARSER.parse(rawMessage);
        }
        log.warn("[ProtocolFactory] 无匹配的检验解析器，尝试默认HL7解析器");
        return HL7_PARSER.parse(rawMessage);
    }

    /**
     * 获取尿机解析器单例
     */
    public static UritUrineProtocolParser getUrineParser() {
        return URIT_PARSER;
    }

    /**
     * 获取HL7解析器单例
     */
    public static Hl7AstmLabProtocolParser getLabParser() {
        return HL7_PARSER;
    }
}
