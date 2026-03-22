package com.ilbuy.supplier.entity;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDateTime;

public class SupplierScoreMain implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long mainId;
    private Long supplierId;
    private String scorePeriod;
    private BigDecimal totalScore;
    private String supplierLevel;
    private String scoreUser;
    private LocalDateTime scoreTime;
    private String opinion;
    private LocalDateTime createTime;

    public Long getMainId() {
        return mainId;
    }

    public void setMainId(Long mainId) {
        this.mainId = mainId;
    }

    public Long getSupplierId() {
        return supplierId;
    }

    public void setSupplierId(Long supplierId) {
        this.supplierId = supplierId;
    }

    public String getScorePeriod() {
        return scorePeriod;
    }

    public void setScorePeriod(String scorePeriod) {
        this.scorePeriod = scorePeriod;
    }

    public BigDecimal getTotalScore() {
        return totalScore;
    }

    public void setTotalScore(BigDecimal totalScore) {
        this.totalScore = totalScore;
    }

    public String getSupplierLevel() {
        return supplierLevel;
    }

    public void setSupplierLevel(String supplierLevel) {
        this.supplierLevel = supplierLevel;
    }

    public String getScoreUser() {
        return scoreUser;
    }

    public void setScoreUser(String scoreUser) {
        this.scoreUser = scoreUser;
    }

    public LocalDateTime getScoreTime() {
        return scoreTime;
    }

    public void setScoreTime(LocalDateTime scoreTime) {
        this.scoreTime = scoreTime;
    }

    public String getOpinion() {
        return opinion;
    }

    public void setOpinion(String opinion) {
        this.opinion = opinion;
    }

    public LocalDateTime getCreateTime() {
        return createTime;
    }

    public void setCreateTime(LocalDateTime createTime) {
        this.createTime = createTime;
    }
}
