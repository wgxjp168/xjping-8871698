package com.ilbuy.shop.dto;

import lombok.Data;
import javax.validation.Valid;
import javax.validation.constraints.*;
import java.math.BigDecimal;
import java.util.List;

@Data
public class ShopScoreDTO {

    @NotNull(message = "商铺ID不能为空")
    private Long shopId;

    @NotBlank(message = "评分周期不能为空")
    private String scorePeriod;

    @NotBlank(message = "评分人不能为空")
    private String scoreUser;

    private String opinion;

    @Valid
    @NotEmpty(message = "评分明细不能为空")
    private List<ScoreItemDTO> itemList;

    @Data
    public static class ScoreItemDTO {

        @NotNull(message = "评分规则不能为空")
        @Min(value = 1, message = "scoreRule 范围 1-6")
        @Max(value = 6, message = "scoreRule 范围 1-6")
        private Integer scoreRule;

        @NotNull(message = "实际分值不能为空")
        @DecimalMin(value = "0", message = "分值不能为负")
        private BigDecimal actualScore;

        private String remark;
    }
}
