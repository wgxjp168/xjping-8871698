package com.ilbuy.shop.dto;

import lombok.Data;
import javax.validation.constraints.*;
import java.time.LocalDate;

@Data
public class ShopInfoDTO {

    /** 新增时为 null，修改时必传 */
    private Long shopId;

    @NotBlank(message = "商铺名称不能为空")
    @Size(max = 100, message = "商铺名称最多100字")
    private String shopName;

    @NotNull(message = "类目ID不能为空")
    private Integer cateId;

    @NotBlank(message = "联系人不能为空")
    @Size(max = 50, message = "联系人最多50字")
    private String contactUser;

    @NotBlank(message = "联系电话不能为空")
    @Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确")
    private String contactPhone;

    private Integer shopStatus;

    private LocalDate joinTime;

    @Size(max = 500, message = "备注最多500字")
    private String remark;
}
