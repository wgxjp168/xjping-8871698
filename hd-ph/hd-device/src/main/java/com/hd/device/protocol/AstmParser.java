package com.hd.device.protocol;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * ASTM E1381/E1394 协议解析器
 * 支持: 生化仪 / 血常规仪 / 尿分析仪 / 糖化血红蛋白仪
 *
 * 物理层控制字符（LIS01-A2 / ASTM E1381）:
 *   SOH=0x01, STX=0x02, ETX=0x03, EOT=0x04, ENQ=0x05, ACK=0x06, NAK=0x15, CR=0x0D, LF=0x0A
 *
 * 典型帧格式: STX + frameNo + data + CR + checksum + ETX/ETB
 * 消息格式:   H|...  P|...  O|...  R|...  L|...
 */
public class AstmParser {

    private static final Logger log = LoggerFactory.getLogger(AstmParser.class);

    public static final byte SOH = 0x01;
    public static final byte STX = 0x02;
    public static final byte ETX = 0x03;
    public static final byte EOT = 0x04;
    public static final byte ENQ = 0x05;
    public static final byte ACK = 0x06;
    public static final byte NAK = 0x15;
    public static final byte CR  = 0x0D;
    public static final byte LF  = 0x0A;
    public static final byte ETB = 0x17;

    /**
     * 从原始字节流中提取数据帧内容（去除控制字符和帧头帧尾）
     * 返回可打印的 ASTM 记录行列表（每行以 CR 结束）
     */
    public static List<String> extractRecordLines(byte[] data) {
        List<String> lines = new ArrayList<>();
        StringBuilder sb = new StringBuilder();
        boolean inFrame = false;

        for (int i = 0; i < data.length; i++) {
            byte b = data[i];
            if (b == STX) {
                // 跳过帧号（STX后一个字节）
                inFrame = true;
                i++; // skip frame number byte
                sb = new StringBuilder();
            } else if (b == ETX || b == ETB) {
                // 帧结束，跳过校验和（2字节）和CR/LF
                inFrame = false;
                // 把缓冲内容按CR分割成行
                String content = sb.toString();
                for (String line : content.split("\r")) {
                    String trimmed = line.trim();
                    if (!trimmed.isEmpty()) {
                        lines.add(trimmed);
                    }
                }
                // 跳过校验和(2字节)
                i += 2;
            } else if (inFrame && b != CR && b != LF) {
                // 注意：CR是记录分隔符，我们保留CR以便后续split
                sb.append((char) b);
            } else if (inFrame && b == CR) {
                sb.append('\r');
            }
        }
        // 如果没有STX/ETX（某些设备直接发送可读文本）
        if (lines.isEmpty() && data.length > 0) {
            String raw = new String(data).replaceAll("[\\x01\\x02\\x03\\x04\\x05\\x06\\x15\\x17]", "");
            for (String line : raw.split("[\r\n]+")) {
                String trimmed = line.trim();
                if (!trimmed.isEmpty()) {
                    lines.add(trimmed);
                }
            }
        }
        return lines;
    }

    /**
     * 将记录行列表解析为 AstmMessage 对象
     */
    public static AstmMessage parseMessage(List<String> lines) {
        AstmMessage msg = new AstmMessage();
        StringBuilder rawText = new StringBuilder();
        for (String line : lines) {
            rawText.append(line).append("\n");
            if (line.isEmpty()) continue;
            char type = line.charAt(0);
            List<String> fields = Arrays.asList(line.split("\\|", -1));
            AstmRecord record = new AstmRecord(String.valueOf(type), fields);
            switch (type) {
                case 'H':
                    msg.setHeaderRecord(record);
                    break;
                case 'P':
                    msg.setPatientRecord(record);
                    break;
                case 'O':
                    msg.setOrderRecord(record);
                    break;
                case 'R':
                    msg.addResultRecord(record);
                    break;
                case 'L':
                    msg.setTerminatorRecord(record);
                    break;
                default:
                    log.debug("未知记录类型: {}", type);
            }
        }
        msg.setRawText(rawText.toString());
        return msg;
    }

    /**
     * 从 R 记录解析单个检验结果
     * R|sequenceNo|testId^^^testName|value|unit|referenceRange|flag
     *
     * @return ParsedResult
     */
    public static ParsedResult parseResultRecord(AstmRecord rRecord) {
        ParsedResult result = new ParsedResult();
        // R|1|^^^WBC|6.5|10^9/L|4.0-10.0|N
        String testIdField = rRecord.getField(2); // ^^^WBC 或 WBC
        if (testIdField.contains("^")) {
            String[] parts = testIdField.split("\\^");
            result.setTestCode(parts.length > 3 ? parts[3] : parts[parts.length - 1]);
            result.setTestName(parts.length > 4 ? parts[4] : result.getTestCode());
        } else {
            result.setTestCode(testIdField);
            result.setTestName(testIdField);
        }
        result.setValue(rRecord.getField(3));
        result.setUnit(rRecord.getField(4));
        result.setReferenceRange(rRecord.getField(5));
        String flag = rRecord.getField(6);
        result.setAbnormal(flag != null && (flag.contains("H") || flag.contains("L") || flag.contains("A")));
        result.setFlag(flag);
        return result;
    }

    /**
     * 验证 ASTM 帧校验和
     */
    public static boolean verifyChecksum(byte[] frame) {
        // 校验和 = STX之后、ETX/ETB之前所有字节之和 mod 256 的十六进制ASCII表示
        int sum = 0;
        int start = -1, end = -1;
        for (int i = 0; i < frame.length; i++) {
            if (frame[i] == STX) { start = i + 1; }
            if ((frame[i] == ETX || frame[i] == ETB) && start >= 0) { end = i; break; }
        }
        if (start < 0 || end < 0) return true; // 无法验证，放行
        for (int i = start; i < end; i++) {
            sum += (frame[i] & 0xFF);
        }
        sum = sum % 256;
        if (end + 2 < frame.length) {
            String expected = String.format("%02X", sum);
            String actual = String.valueOf((char) frame[end + 1]) + (char) frame[end + 2];
            return expected.equalsIgnoreCase(actual);
        }
        return true;
    }
}
