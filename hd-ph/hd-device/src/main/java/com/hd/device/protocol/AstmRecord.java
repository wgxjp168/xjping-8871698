package com.hd.device.protocol;

import java.util.ArrayList;
import java.util.List;

/**
 * ASTM E1394 解析后的报文结构
 */
public class AstmRecord {

    /** 报文类型: H=头, P=患者, O=样本, R=结果, L=结束 */
    private String recordType;

    /** 原始字段列表（以|分割） */
    private List<String> fields = new ArrayList<>();

    public AstmRecord(String recordType, List<String> fields) {
        this.recordType = recordType;
        this.fields = fields;
    }

    public String getRecordType() {
        return recordType;
    }

    public List<String> getFields() {
        return fields;
    }

    public String getField(int index) {
        if (index < fields.size()) {
            return fields.get(index);
        }
        return "";
    }

    @Override
    public String toString() {
        return recordType + ": " + String.join("|", fields);
    }
}
