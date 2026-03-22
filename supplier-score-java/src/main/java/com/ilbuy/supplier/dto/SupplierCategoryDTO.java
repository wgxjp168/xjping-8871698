package com.ilbuy.supplier.dto;

import lombok.Data;

import javax.validation.constraints.Min;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.Size;

@Data
public class SupplierCategoryDTO {

    /** 修改时必传 */
    private Integer id;

    @NotBlank(message = "分类名称不能为空")
    @Size(max = 50, message = "分类名称最多50字")
    private String cateName;

    @Min(value = 0, message = "排序值不能为负")
    private Integer sort = 0;

    /** 1启用 0禁用 */
    private Integer status = 1;
}
