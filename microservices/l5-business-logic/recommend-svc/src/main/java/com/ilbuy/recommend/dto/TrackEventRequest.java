package com.ilbuy.recommend.dto;

import com.ilbuy.recommend.model.enums.EventType;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class TrackEventRequest {

    @NotNull(message = "eventType is required")
    private EventType eventType;

    private Long productId;

    private Long canonicalId;

    private String category;

    private String platform;

    private String keyword;
}
