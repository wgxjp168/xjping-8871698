package com.ilbuy.product.model.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CategoryDTO {

    private Long id;
    private String name;
    private Long parentId;
    private String description;
    private Integer sortOrder;
    private String iconUrl;
    private Boolean enabled;

    /** Child categories (populated when building tree) */
    private List<CategoryDTO> children;
}
