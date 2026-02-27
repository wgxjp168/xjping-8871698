package com.ilbuy.business;

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
class BusinessLogicApplicationTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void contextLoads() {}

    @Test
    void statusEndpoint() throws Exception {
        mockMvc.perform(get("/api/status"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.service").value("ILbuy Business Logic Layer"))
                .andExpect(jsonPath("$.status").value("running"));
    }

    // --- User Tests ---

    @Test
    void listUsers() throws Exception {
        mockMvc.perform(get("/api/users"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(greaterThanOrEqualTo(3))));
    }

    @Test
    void getUserById() throws Exception {
        mockMvc.perform(get("/api/users/U001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.username").value("zhangsan"))
                .andExpect(jsonPath("$.memberLevel").value("VIP"));
    }

    @Test
    void createUser() throws Exception {
        mockMvc.perform(post("/api/users")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"username":"testuser","email":"test@ilbuy.com","phone":"13900001111","nickname":"测试用户"}
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").exists())
                .andExpect(jsonPath("$.username").value("testuser"));
    }

    // --- Product Tests ---

    @Test
    void listProducts() throws Exception {
        mockMvc.perform(get("/api/products"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(greaterThanOrEqualTo(8))));
    }

    @Test
    void listProductsByCategory() throws Exception {
        mockMvc.perform(get("/api/products").param("category", "electronics"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].category").value("electronics"));
    }

    @Test
    void getProductById() throws Exception {
        mockMvc.perform(get("/api/products/P001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("智能手表Pro"))
                .andExpect(jsonPath("$.price").value(1299.0));
    }

    // --- Cart Tests ---

    @Test
    void cartAddAndGet() throws Exception {
        mockMvc.perform(post("/api/cart/testUser/items")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"productId":"P001","quantity":2}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.userId").value("testUser"))
                .andExpect(jsonPath("$.items", hasSize(1)))
                .andExpect(jsonPath("$.items[0].productName").value("智能手表Pro"));

        mockMvc.perform(get("/api/cart/testUser"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalAmount").value(2598.0));
    }

    // --- Order Tests ---

    @Test
    void createAndGetOrder() throws Exception {
        String orderBody = """
                {
                    "userId": "U001",
                    "shippingAddress": "北京市朝阳区XX路XX号",
                    "paymentMethod": "ALIPAY",
                    "items": [
                        {"productId": "P002", "quantity": 1},
                        {"productId": "P004", "quantity": 2}
                    ]
                }
                """;
        String response = mockMvc.perform(post("/api/orders")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(orderBody))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.userId").value("U001"))
                .andExpect(jsonPath("$.status").value("PENDING"))
                .andExpect(jsonPath("$.items", hasSize(2)))
                .andExpect(jsonPath("$.totalAmount").value(1235.0))
                .andReturn().getResponse().getContentAsString();

        String orderId = com.fasterxml.jackson.databind.ObjectMapper
                .class.getDeclaredConstructor().newInstance()
                .readTree(response).get("id").asText();

        mockMvc.perform(get("/api/orders/" + orderId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(orderId));
    }

    @Test
    void productNotFound() throws Exception {
        mockMvc.perform(get("/api/products/NONEXISTENT"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error").value("NOT_FOUND"));
    }
}
