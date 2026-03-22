package com.ilbuy.shop.dto;

import lombok.Data;
import javax.validation.constraints.*;

@Data
public class ShopCategoryDTO {

    /** 修改时必传 */
    private Integer id;

    @NotBlank(message = "类目名称不能为空")
    @Size(max = 50, message = "类目名称最多50字")
    private String cateName;

    @Min(value = 0, message = "排序值不能为负")
    private Integer sort = 0;

    /** 1启用 0禁用 */
    private Integer status = 1;
}
