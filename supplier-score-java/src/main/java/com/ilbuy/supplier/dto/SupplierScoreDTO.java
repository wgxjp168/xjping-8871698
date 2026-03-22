package com.ilbuy.supplier.dto;

import javax.validation.Valid;
import javax.validation.constraints.DecimalMin;
import javax.validation.constraints.Max;
import javax.validation.constraints.Min;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotEmpty;
import javax.validation.constraints.NotNull;
import java.io.Serializable;
import java.math.BigDecimal;
import java.util.List;

public class SupplierScoreDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    @NotNull(message = "供应商ID不能为空")
    private Long supplierId;

    @NotBlank(message = "评分周期不能为空")
    private String scorePeriod;

    @NotBlank(message = "评分人不能为空")
    private String scoreUser;

    private String opinion;

    @Valid
    @NotEmpty(message = "评分明细不能为空")
    private List<ItemDTO> itemList;

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

    public String getScoreUser() {
        return scoreUser;
    }

    public void setScoreUser(String scoreUser) {
        this.scoreUser = scoreUser;
    }

    public String getOpinion() {
        return opinion;
    }

    public void setOpinion(String opinion) {
        this.opinion = opinion;
    }

    public List<ItemDTO> getItemList() {
        return itemList;
    }

    public void setItemList(List<ItemDTO> itemList) {
        this.itemList = itemList;
    }

    public static class ItemDTO implements Serializable {

        private static final long serialVersionUID = 1L;

        @NotNull(message = "评分类型不能为空")
        @Min(value = 1, message = "评分类型最小为1")
        @Max(value = 6, message = "评分类型最大为6")
        private Integer scoreType;

        @NotNull(message = "实际分值不能为空")
        @DecimalMin(value = "0", message = "实际分值不能为负数")
        private BigDecimal actualScore;

        private String remark;

        public Integer getScoreType() {
            return scoreType;
        }

        public void setScoreType(Integer scoreType) {
            this.scoreType = scoreType;
        }

        public BigDecimal getActualScore() {
            return actualScore;
        }

        public void setActualScore(BigDecimal actualScore) {
            this.actualScore = actualScore;
        }

        public String getRemark() {
            return remark;
        }

        public void setRemark(String remark) {
            this.remark = remark;
        }
    }
}
