package com.ilbuy.product.model.dto;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

@Data
public class CompareRequest {

    @NotEmpty(message = "ids must not be empty")
    @Size(min = 2, max = 4, message = "Please provide between 2 and 4 product ids to compare")
    private List<Long> ids;
}
