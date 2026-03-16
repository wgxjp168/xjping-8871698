package com.ilbuy.recommend.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class HomepageRecommendDTO {

    private List<RecommendItemDTO> hot;
    private List<RecommendItemDTO> forYou;
    private List<RecommendItemDTO> newArrivals;
}
