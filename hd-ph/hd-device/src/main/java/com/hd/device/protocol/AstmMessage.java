package com.hd.device.protocol;

import java.util.ArrayList;
import java.util.List;

/**
 * 一次完整的 ASTM 传输消息（H...L）
 */
public class AstmMessage {

    private AstmRecord headerRecord;
    private AstmRecord patientRecord;
    private AstmRecord orderRecord;
    private List<AstmRecord> resultRecords = new ArrayList<>();
    private AstmRecord terminatorRecord;

    /** 原始完整消息文本 */
    private String rawText;

    public AstmRecord getHeaderRecord() { return headerRecord; }
    public void setHeaderRecord(AstmRecord headerRecord) { this.headerRecord = headerRecord; }
    public AstmRecord getPatientRecord() { return patientRecord; }
    public void setPatientRecord(AstmRecord patientRecord) { this.patientRecord = patientRecord; }
    public AstmRecord getOrderRecord() { return orderRecord; }
    public void setOrderRecord(AstmRecord orderRecord) { this.orderRecord = orderRecord; }
    public List<AstmRecord> getResultRecords() { return resultRecords; }
    public void addResultRecord(AstmRecord r) { this.resultRecords.add(r); }
    public AstmRecord getTerminatorRecord() { return terminatorRecord; }
    public void setTerminatorRecord(AstmRecord terminatorRecord) { this.terminatorRecord = terminatorRecord; }
    public String getRawText() { return rawText; }
    public void setRawText(String rawText) { this.rawText = rawText; }

    /**
     * 从 O 记录第 3 个字段获取样本号
     * O|1|SAMPLE_ID|...
     */
    public String getSampleId() {
        if (orderRecord != null) {
            return orderRecord.getField(2);
        }
        return null;
    }

    /**
     * 从 P 记录第 3 个字段获取患者ID
     * P|1|PATIENT_ID|...
     */
    public String getPatientId() {
        if (patientRecord != null) {
            return patientRecord.getField(2);
        }
        return null;
    }
}
