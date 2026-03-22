package com.ilbuy.supplier.vo;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Data
public class SupplierScoreDetailVO {

    private Long   mainId;
    private Long   supplierId;
    private String supplierName;
    private String scorePeriod;
    private BigDecimal totalScore;
    private String supplierLevel;
    private String scoreUser;
    private LocalDateTime scoreTime;
    private String opinion;

    /** 各维度明细 */
    private List<ItemVO> itemList;

    @Data
    public static class ItemVO {
        private Integer scoreType;
        private String  scoreTypeName;
        private BigDecimal fullScore;
        private BigDecimal actualScore;
        private String  remark;
    }
}
