package com.ilbuy.ai.controller;

import com.ilbuy.ai.model.DecisionContext;
import com.ilbuy.ai.model.DecisionResult;
import com.ilbuy.ai.service.DecisionService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.Map;

@RestController
@RequestMapping("/api/ai")
public class DecisionController {

    private final DecisionService decisionService;

    public DecisionController(DecisionService decisionService) {
        this.decisionService = decisionService;
    }

    @PostMapping("/decide")
    public ResponseEntity<DecisionResult> makeDecision(
            @Valid @RequestBody DecisionContext context) {
        return ResponseEntity.ok(decisionService.makeDecision(context));
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> status() {
        return ResponseEntity.ok(Map.of(
                "service", "ILbuy AI Decision Hub",
                "status", "running",
                "version", "1.0.0-SNAPSHOT",
                "capabilities", Map.of(
                        "recommendation", "商品智能推荐",
                        "pricing", "AI智能定价",
                        "decision", "通用AI决策(购买意图/风控/用户分群)"
                ),
                "timestamp", LocalDateTime.now().toString()
        ));
    }
}
