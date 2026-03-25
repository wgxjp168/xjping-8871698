package com.hd.device.protocol;

/**
 * ASTM R记录解析结果
 */
public class ParsedResult {

    private String testCode;
    private String testName;
    private String value;
    private String unit;
    private String referenceRange;
    private String flag;
    private boolean abnormal;

    public String getTestCode() { return testCode; }
    public void setTestCode(String testCode) { this.testCode = testCode; }
    public String getTestName() { return testName; }
    public void setTestName(String testName) { this.testName = testName; }
    public String getValue() { return value; }
    public void setValue(String value) { this.value = value; }
    public String getUnit() { return unit; }
    public void setUnit(String unit) { this.unit = unit; }
    public String getReferenceRange() { return referenceRange; }
    public void setReferenceRange(String referenceRange) { this.referenceRange = referenceRange; }
    public String getFlag() { return flag; }
    public void setFlag(String flag) { this.flag = flag; }
    public boolean isAbnormal() { return abnormal; }
    public void setAbnormal(boolean abnormal) { this.abnormal = abnormal; }

    @Override
    public String toString() {
        return testCode + "=" + value + " " + unit + (abnormal ? " [" + flag + "]" : "");
    }
}
