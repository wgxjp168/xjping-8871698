package com.ilbuy.supplier.entity;

import java.io.Serializable;
import java.time.LocalDateTime;

public class SupplierAbnormal implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long id;
    private Long supplierId;
    private String abnType;
    private String abnContent;
    private LocalDateTime abnTime;
    private Integer deductionScore;
    private String handleResult;
    private LocalDateTime createTime;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getSupplierId() {
        return supplierId;
    }

    public void setSupplierId(Long supplierId) {
        this.supplierId = supplierId;
    }

    public String getAbnType() {
        return abnType;
    }

    public void setAbnType(String abnType) {
        this.abnType = abnType;
    }

    public String getAbnContent() {
        return abnContent;
    }

    public void setAbnContent(String abnContent) {
        this.abnContent = abnContent;
    }

    public LocalDateTime getAbnTime() {
        return abnTime;
    }

    public void setAbnTime(LocalDateTime abnTime) {
        this.abnTime = abnTime;
    }

    public Integer getDeductionScore() {
        return deductionScore;
    }

    public void setDeductionScore(Integer deductionScore) {
        this.deductionScore = deductionScore;
    }

    public String getHandleResult() {
        return handleResult;
    }

    public void setHandleResult(String handleResult) {
        this.handleResult = handleResult;
    }

    public LocalDateTime getCreateTime() {
        return createTime;
    }

    public void setCreateTime(LocalDateTime createTime) {
        this.createTime = createTime;
    }
}
