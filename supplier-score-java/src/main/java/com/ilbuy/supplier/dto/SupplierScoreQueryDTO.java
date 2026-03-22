package com.ilbuy.supplier.dto;

import com.ilbuy.supplier.common.PageQuery;

public class SupplierScoreQueryDTO extends PageQuery {

    private Long supplierId;
    private String supplierName;
    private String scorePeriod;
    private String supplierLevel;

    public Long getSupplierId() {
        return supplierId;
    }

    public void setSupplierId(Long supplierId) {
        this.supplierId = supplierId;
    }

    public String getSupplierName() {
        return supplierName;
    }

    public void setSupplierName(String supplierName) {
        this.supplierName = supplierName;
    }

    public String getScorePeriod() {
        return scorePeriod;
    }

    public void setScorePeriod(String scorePeriod) {
        this.scorePeriod = scorePeriod;
    }

    public String getSupplierLevel() {
        return supplierLevel;
    }

    public void setSupplierLevel(String supplierLevel) {
        this.supplierLevel = supplierLevel;
    }
}
