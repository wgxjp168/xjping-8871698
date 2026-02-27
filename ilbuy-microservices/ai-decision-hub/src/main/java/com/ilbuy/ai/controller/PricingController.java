package com.ilbuy.ai.controller;

import com.ilbuy.ai.model.PricingRequest;
import com.ilbuy.ai.model.PricingResult;
import com.ilbuy.ai.service.PricingService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/ai/pricing")
public class PricingController {

    private final PricingService pricingService;

    public PricingController(PricingService pricingService) {
        this.pricingService = pricingService;
    }

    @PostMapping
    public ResponseEntity<PricingResult> calculatePrice(
            @Valid @RequestBody PricingRequest request) {
        return ResponseEntity.ok(pricingService.calculatePrice(request));
    }
}
