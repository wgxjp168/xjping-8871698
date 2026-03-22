package com.ilbuy.shop.vo;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Data
public class ShopScoreDetailVO {

    private Long   mainId;
    private Long   shopId;
    private String shopName;
    private String scorePeriod;
    private BigDecimal totalScore;
    private String shopLevel;
    private String scoreUser;
    private LocalDateTime scoreTime;
    private String opinion;

    /** 各维度明细 */
    private List<ItemVO> itemList;

    @Data
    public static class ItemVO {
        private Integer scoreRule;
        private String  scoreRuleName;
        private BigDecimal fullScore;
        private BigDecimal actualScore;
        private String  remark;
    }
}
