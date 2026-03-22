package com.ilbuy.shop.dto;

import lombok.Data;
import javax.validation.constraints.*;
import java.time.LocalDateTime;

@Data
public class ShopViolationDTO {

    @NotNull(message = "商铺ID不能为空")
    private Long shopId;

    @NotBlank(message = "违规类型不能为空")
    @Size(max = 50, message = "违规类型最多50字")
    private String vioType;

    @NotBlank(message = "违规内容不能为空")
    @Size(max = 500, message = "违规内容最多500字")
    private String vioContent;

    @NotNull(message = "违规时间不能为空")
    private LocalDateTime vioTime;

    @Min(value = 0, message = "扣分不能为负")
    private Integer deductionScore = 0;

    @Size(max = 200, message = "处理结果最多200字")
    private String handleResult;
}
