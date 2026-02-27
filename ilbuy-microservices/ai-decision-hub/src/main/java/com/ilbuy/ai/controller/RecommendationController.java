package com.ilbuy.ai.controller;

import com.ilbuy.ai.model.RecommendationRequest;
import com.ilbuy.ai.model.RecommendationResult;
import com.ilbuy.ai.service.RecommendationService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/ai/recommendations")
public class RecommendationController {

    private final RecommendationService recommendationService;

    public RecommendationController(RecommendationService recommendationService) {
        this.recommendationService = recommendationService;
    }

    @PostMapping
    public ResponseEntity<RecommendationResult> getRecommendations(
            @Valid @RequestBody RecommendationRequest request) {
        return ResponseEntity.ok(recommendationService.recommend(request));
    }

    @GetMapping("/{userId}")
    public ResponseEntity<RecommendationResult> getRecommendationsForUser(
            @PathVariable String userId,
            @RequestParam(required = false) String category,
            @RequestParam(defaultValue = "10") int limit) {
        RecommendationRequest request = new RecommendationRequest(userId, category, limit);
        return ResponseEntity.ok(recommendationService.recommend(request));
    }
}
