package com.ilbuy.data;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.hamcrest.Matchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class DataLayerApplicationTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void contextLoads() {}

    @Test
    void statusEndpoint() throws Exception {
        mockMvc.perform(get("/api/data/status"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.service").value("ILbuy Data Layer"))
                .andExpect(jsonPath("$.database").value("H2 (in-memory)"));
    }

    @Test
    void listUsersFromDb() throws Exception {
        mockMvc.perform(get("/api/data/users"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(greaterThanOrEqualTo(3))));
    }

    @Test
    void listProductsFromDb() throws Exception {
        mockMvc.perform(get("/api/data/products"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(greaterThanOrEqualTo(8))));
    }

    @Test
    void searchProducts() throws Exception {
        mockMvc.perform(get("/api/data/products/search").param("q", "智能"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(greaterThanOrEqualTo(2))));
    }

    @Test
    void createAndQueryOrder() throws Exception {
        mockMvc.perform(post("/api/data/orders")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"userId":"test-user","shippingAddress":"测试地址","paymentMethod":"WECHAT","status":"PENDING","totalAmount":100.0}
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").exists());

        mockMvc.perform(get("/api/data/orders").param("userId", "test-user"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(greaterThanOrEqualTo(1))));
    }

    @Test
    void statsEndpoint() throws Exception {
        mockMvc.perform(get("/api/data/stats"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.userCount").value(greaterThanOrEqualTo(3)))
                .andExpect(jsonPath("$.productCount").value(greaterThanOrEqualTo(8)));
    }
}
