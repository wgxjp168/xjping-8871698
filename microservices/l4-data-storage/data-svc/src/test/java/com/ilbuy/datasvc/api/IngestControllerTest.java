package com.ilbuy.datasvc.api;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ilbuy.datasvc.model.dto.IngestRequest;
import com.ilbuy.datasvc.model.dto.IngestResponse;
import com.ilbuy.datasvc.model.dto.ProductIngestDTO;
import com.ilbuy.datasvc.service.IngestService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(IngestController.class)
class IngestControllerTest {

    @Autowired MockMvc mockMvc;
    @Autowired ObjectMapper objectMapper;
    @MockBean  IngestService ingestService;

    @Test
    void postIngest_validRequest_returns200() throws Exception {
        IngestRequest req = buildRequest();
        IngestResponse resp = IngestResponse.builder()
            .jobId("job-1").sessionId("sess-1")
            .total(1).saved(1).failed(0)
            .durationMs(50).processedAt(Instant.now())
            .status("success").build();

        when(ingestService.ingest(any())).thenReturn(resp);

        mockMvc.perform(post("/ingest")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(req)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("success"))
            .andExpect(jsonPath("$.saved").value(1))
            .andExpect(jsonPath("$.failed").value(0));
    }

    @Test
    void postIngest_missingJobId_returns400() throws Exception {
        IngestRequest req = new IngestRequest();
        // jobId missing

        mockMvc.perform(post("/ingest")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(req)))
            .andExpect(status().isBadRequest());
    }

    @Test
    void postIngest_emptyProducts_returns400() throws Exception {
        IngestRequest req = new IngestRequest();
        req.setJobId("job-x");
        req.setSessionId("sess-x");
        req.setProducts(List.of());  // @NotEmpty fails

        mockMvc.perform(post("/ingest")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(req)))
            .andExpect(status().isBadRequest());
    }

    private IngestRequest buildRequest() {
        ProductIngestDTO dto = new ProductIngestDTO();
        dto.setCanonicalId("cid-001");
        dto.setPlatform("jd");
        dto.setProductId("jd_001");
        dto.setTitle("小米手机");
        dto.setPrice(new BigDecimal("999.00"));

        IngestRequest req = new IngestRequest();
        req.setJobId("job-1");
        req.setSessionId("sess-1");
        req.setProducts(List.of(dto));
        return req;
    }
}
