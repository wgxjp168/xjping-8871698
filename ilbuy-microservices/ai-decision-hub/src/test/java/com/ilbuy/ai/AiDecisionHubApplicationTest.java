package com.ilbuy.ai;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class AiDecisionHubApplicationTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void contextLoads() {
    }

    @Test
    void statusEndpoint() throws Exception {
        mockMvc.perform(get("/api/ai/status"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.service").value("ILbuy AI Decision Hub"))
                .andExpect(jsonPath("$.status").value("running"))
                .andExpect(jsonPath("$.capabilities.recommendation").value("商品智能推荐"));
    }

    @Test
    void recommendationByUserId() throws Exception {
        mockMvc.perform(get("/api/ai/recommendations/user123")
                        .param("limit", "5"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.userId").value("user123"))
                .andExpect(jsonPath("$.strategy").exists())
                .andExpect(jsonPath("$.recommendations").isArray());
    }

    @Test
    void recommendationPost() throws Exception {
        String body = """
                {"userId":"user456","category":"electronics","limit":3}
                """;
        mockMvc.perform(post("/api/ai/recommendations")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.userId").value("user456"))
                .andExpect(jsonPath("$.strategy").value("category-filtered-collaborative"));
    }

    @Test
    void pricingEndpoint() throws Exception {
        String body = """
                {"productId":"P001","basePrice":1299.00,"category":"electronics","stockQuantity":50,"demandLevel":9}
                """;
        mockMvc.perform(post("/api/ai/pricing")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.productId").value("P001"))
                .andExpect(jsonPath("$.strategy").value("high-demand-premium"))
                .andExpect(jsonPath("$.suggestedPrice").exists());
    }

    @Test
    void decisionEndpoint() throws Exception {
        String body = """
                {"decisionType":"purchase_intent","inputData":"browsing_electronics","userId":"user789"}
                """;
        mockMvc.perform(post("/api/ai/decide")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.decisionType").value("purchase_intent"))
                .andExpect(jsonPath("$.outcome").value("high_intent"))
                .andExpect(jsonPath("$.confidence").exists());
    }

    @Test
    void fraudDetectionDecision() throws Exception {
        String body = """
                {"decisionType":"fraud_detection","inputData":"order_check","userId":"user999"}
                """;
        mockMvc.perform(post("/api/ai/decide")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.outcome").value("safe"))
                .andExpect(jsonPath("$.details.risk_level").value("low"));
    }
}
