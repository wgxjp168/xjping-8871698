package com.ilbuy.ops;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class SupportOpsApplicationTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void contextLoads() {}

    @Test
    void statusEndpoint() throws Exception {
        mockMvc.perform(get("/api/ops/status"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.service").value("ILbuy Support & Ops Layer"));
    }

    @Test
    void serviceRegistryEndpoint() throws Exception {
        mockMvc.perform(get("/api/ops/services"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.services.access-layer.port").value(8080));
    }

    @Test
    void dashboardEndpoint() throws Exception {
        mockMvc.perform(get("/api/ops/dashboard"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.platform").value("ILbuy (我来购) AI智能体微服务平台"));
    }
}
