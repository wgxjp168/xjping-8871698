# 我来购ILbuy 集成测试用例

## 概述

| 属性 | 说明 |
|------|------|
| 项目名称 | 我来购ILbuy采购平台 |
| 测试类型 | 集成测试（Integration Test） |
| 测试框架 | Spring Boot Test + TestContainers + RestAssured |
| 测试范围 | 微服务间RPC调用、消息队列、数据库事务 |
| 执行方式 | `mvn verify -P integration-test` |

---

## 一、采购需求→AI匹配 集成流程

### TC-INT-001 完整采购匹配链路

**场景描述：** 用户创建采购需求后，系统自动触发AI匹配，通过消息队列异步处理，最终更新匹配结果

**测试步骤：**

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Testcontainers
@ActiveProfiles("integration-test")
class ProcurementMatchingIntegrationTest {

    @Container
    static MySQLContainer<?> mysql = new MySQLContainer<>("mysql:8.0")
        .withDatabaseName("ilbuy_test");

    @Container
    static GenericContainer<?> redis = new GenericContainer<>("redis:7.0")
        .withExposedPorts(6379);

    @Container
    static GenericContainer<?> kafka = new GenericContainer<>("confluentinc/cp-kafka:7.4.0")
        .withExposedPorts(9092);

    @Autowired private TestRestTemplate restTemplate;
    @Autowired private ProcurementRepository procurementRepo;
    @Autowired private MatchingResultRepository matchingResultRepo;

    @Test
    @DisplayName("TC-INT-001: 采购需求创建→消息发送→AI匹配→结果回写完整链路")
    @Timeout(value = 60, unit = TimeUnit.SECONDS)
    void testFullProcurementMatchingFlow() throws InterruptedException {
        // Step 1: 创建采购需求
        String token = login("test_buyer_001", "Test@123456");
        ProcurementCreateRequest req = buildB2BRequest();

        ResponseEntity<ApiResponse<ProcurementCreateResponse>> createResp =
            restTemplate.exchange(
                "/api/v1/procurement/demands",
                HttpMethod.POST,
                buildHttpEntity(req, token),
                new ParameterizedTypeReference<>() {}
            );

        assertThat(createResp.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        Long demandId = createResp.getBody().getData().getDemandId();

        // Step 2: 验证消息队列收到消息（最多等待10秒）
        await().atMost(10, SECONDS).untilAsserted(() -> {
            Procurement demand = procurementRepo.findById(demandId).orElseThrow();
            assertThat(demand.getStatus()).isEqualTo(ProcurementStatus.MATCHING);
        });

        // Step 3: 等待AI匹配完成（最多等待30秒）
        await().atMost(30, SECONDS).untilAsserted(() -> {
            List<MatchingResult> results = matchingResultRepo.findByDemandId(demandId);
            assertThat(results).isNotEmpty();
            assertThat(results.get(0).getStatus()).isEqualTo(MatchingStatus.COMPLETED);
        });

        // Step 4: 验证需求状态已更新
        Procurement updatedDemand = procurementRepo.findById(demandId).orElseThrow();
        assertThat(updatedDemand.getStatus()).isEqualTo(ProcurementStatus.QUOTED);
        assertThat(updatedDemand.getMatchedSupplierCount()).isGreaterThan(0);

        // Step 5: 通过API验证结果可查询
        ResponseEntity<ApiResponse<ProcurementDetailResponse>> detailResp =
            restTemplate.exchange(
                "/api/v1/procurement/demands/" + demandId,
                HttpMethod.GET,
                buildHttpEntity(null, token),
                new ParameterizedTypeReference<>() {}
            );

        ProcurementDetailResponse detail = detailResp.getBody().getData();
        assertThat(detail.getMatchedSuppliers()).hasSizeGreaterThanOrEqualTo(1);
        assertThat(detail.getMatchedSuppliers().get(0).getScore()).isBetween(0.0, 100.0);
    }
}
```

**预期结果：**
1. 采购需求创建成功，状态为 MATCHING
2. Kafka 消息在 10 秒内被消费
3. AI 匹配在 30 秒内完成
4. 匹配结果写入数据库
5. 采购需求状态变更为 QUOTED
6. API 可查询到匹配供应商列表

---

## 二、询价→报价→下单 集成流程

### TC-INT-002 B2B采购完整交易链路

```java
@Test
@DisplayName("TC-INT-002: 询价→供应商报价→接受报价→自动创建订单")
void testFullInquiryToOrderFlow() {
    // Step 1: 买家发起询价
    String buyerToken = login("buyer_001", "Test@123456");
    String supplierToken = login("supplier_001", "Test@123456");

    InquiryCreateRequest inquiryReq = InquiryCreateRequest.builder()
        .demandId(existingDemandId)
        .supplierIds(Arrays.asList(5001L, 5002L))
        .deadline(LocalDateTime.now().plusHours(24))
        .build();

    Long inquiryId = createInquiry(buyerToken, inquiryReq);

    // Step 2: 验证供应商收到询价通知
    await().atMost(5, SECONDS).untilAsserted(() -> {
        List<Notification> notifications = notificationRepo.findByRecipientId(5001L);
        assertThat(notifications).anyMatch(n -> n.getType().equals("INQUIRY_RECEIVED"));
    });

    // Step 3: 供应商提交报价
    QuoteSubmitRequest quoteReq = QuoteSubmitRequest.builder()
        .unitPrice(new BigDecimal("46.50"))
        .totalAmount(new BigDecimal("4650.00"))
        .deliveryDays(2)
        .validDays(7)
        .build();

    Long quoteId = submitQuote(supplierToken, inquiryId, quoteReq);

    // Step 4: 买家接受报价
    acceptQuote(buyerToken, inquiryId, quoteId);

    // Step 5: 验证自动创建订单
    await().atMost(10, SECONDS).untilAsserted(() -> {
        List<Order> orders = orderRepo.findByDemandId(existingDemandId);
        assertThat(orders).hasSize(1);
        assertThat(orders.get(0).getStatus()).isEqualTo(OrderStatus.PENDING_PAYMENT);
    });

    // Step 6: 验证询价状态变更
    Inquiry inquiry = inquiryRepo.findById(inquiryId).orElseThrow();
    assertThat(inquiry.getStatus()).isEqualTo(InquiryStatus.ACCEPTED);

    // Step 7: 验证采购需求状态变更
    Procurement demand = procurementRepo.findById(existingDemandId).orElseThrow();
    assertThat(demand.getStatus()).isEqualTo(ProcurementStatus.CONFIRMED);
}
```

---

## 三、Nacos配置中心集成测试

### TC-INT-010 配置动态刷新

```java
@Test
@DisplayName("TC-INT-010: Nacos配置变更动态推送到服务")
void testNacosDynamicConfigRefresh() throws Exception {
    // 初始限流配置
    assertThat(rateLimitConfig.getRequestsPerSecond()).isEqualTo(100);

    // 通过Nacos API更新配置
    nacosConfigService.publishConfig(
        "ilbuy-gateway-dev.yaml",
        "DEFAULT_GROUP",
        "rateLimit:\n  requestsPerSecond: 200"
    );

    // 等待配置刷新（Nacos长轮询默认30秒，测试环境设为3秒）
    await().atMost(10, SECONDS).untilAsserted(() ->
        assertThat(rateLimitConfig.getRequestsPerSecond()).isEqualTo(200)
    );
}
```

---

## 四、Seata分布式事务集成测试

### TC-INT-020 跨服务事务回滚

```java
@Test
@DisplayName("TC-INT-020: 订单创建时库存扣减失败应触发全局回滚")
void testDistributedTransactionRollback() {
    // 模拟库存服务抛出异常
    when(inventoryServiceFeignClient.deductStock(any()))
        .thenThrow(new InsufficientStockException("库存不足"));

    Long initialOrderCount = orderRepo.count();
    Long initialPaymentCount = paymentRepo.count();

    // 执行下单
    assertThatThrownBy(() -> orderService.createOrderWithTransaction(buildOrderRequest()))
        .isInstanceOf(TransactionException.class);

    // 验证所有服务数据均已回滚
    await().atMost(15, SECONDS).untilAsserted(() -> {
        assertThat(orderRepo.count()).isEqualTo(initialOrderCount);     // 订单未创建
        assertThat(paymentRepo.count()).isEqualTo(initialPaymentCount); // 支付记录未创建
    });
}
```

---

## 五、消息队列可靠性测试

### TC-INT-030 消息消费失败重试

```java
@Test
@DisplayName("TC-INT-030: 消息消费失败后按配置重试，超出次数进入死信队列")
void testMessageRetryAndDeadLetter() throws InterruptedException {
    // 模拟消费者前3次处理失败
    AtomicInteger callCount = new AtomicInteger(0);
    doAnswer(inv -> {
        if (callCount.incrementAndGet() <= 3) {
            throw new RuntimeException("处理失败，触发重试");
        }
        return null;
    }).when(matchingMessageHandler).handle(any());

    // 发送测试消息
    kafkaTemplate.send("procurement.matching", buildMatchingMessage());

    // 等待重试完成（最多45秒）
    await().atMost(45, SECONDS).untilAsserted(() ->
        assertThat(callCount.get()).isEqualTo(4) // 1次原始 + 3次重试
    );

    // 第4次处理成功（callCount=4时不抛异常）
    verify(matchingMessageHandler, times(4)).handle(any());
}

@Test
@DisplayName("TC-INT-031: 超出最大重试次数进入死信队列")
void testDeadLetterQueue() throws InterruptedException {
    // 模拟消费者始终失败（超过3次重试）
    doThrow(new RuntimeException("永久失败")).when(matchingMessageHandler).handle(any());

    kafkaTemplate.send("procurement.matching", buildMatchingMessage());

    // 等待死信队列收到消息
    await().atMost(60, SECONDS).untilAsserted(() -> {
        List<ConsumerRecord<String, String>> dlqMessages =
            kafkaTestUtils.getRecords(deadLetterConsumer);
        assertThat(dlqMessages).hasSize(1);
    });

    verify(alertService, times(1)).sendDlqAlert(any());
}
```

---

## 六、微服务熔断集成测试

### TC-INT-040 Sentinel熔断降级

```java
@Test
@DisplayName("TC-INT-040: AI服务不可用时触发熔断，使用规则引擎降级")
void testCircuitBreakerFallback() {
    // 模拟AI服务连续失败，触发熔断
    when(aiServiceFeignClient.match(any()))
        .thenThrow(new ServiceUnavailableException("AI服务不可用"));

    // 连续发送10个请求，触发熔断
    for (int i = 0; i < 10; i++) {
        try {
            matchingService.matchWithAi(buildDemand());
        } catch (Exception e) {
            // 预期前10个请求抛异常
        }
    }

    // 第11个请求应走降级（不抛异常，返回规则引擎结果）
    MatchingResult result = matchingService.matchWithAi(buildDemand());
    assertThat(result.getSource()).isEqualTo("RULE_ENGINE_FALLBACK");
    assertThat(result.getRecommendations()).isNotEmpty();

    // 验证熔断指标上报
    verify(metricsCollector, atLeastOnce()).recordCircuitBreaker("ai-matching-service", "OPEN");
}
```

---

## 七、数据采集→价格更新 集成测试

### TC-INT-050 价格数据采集流程

```java
@Test
@DisplayName("TC-INT-050: 爬虫采集→数据清洗→价格更新完整链路")
void testPriceDataCollectionFlow() {
    // Step 1: 触发价格采集任务
    dataCollectionService.triggerCollection("A4打印纸", Arrays.asList("JD", "TAOBAO"));

    // Step 2: 等待采集完成
    await().atMost(30, SECONDS).untilAsserted(() -> {
        List<RawPriceData> rawData = rawPriceDataRepo.findByKeyword("A4打印纸");
        assertThat(rawData).hasSizeGreaterThanOrEqualTo(2);
    });

    // Step 3: 等待数据清洗和写入
    await().atMost(20, SECONDS).untilAsserted(() -> {
        List<MarketPrice> prices = marketPriceRepo.findByKeyword("A4打印纸");
        assertThat(prices)
            .hasSizeGreaterThanOrEqualTo(2)
            .allMatch(p -> p.getPrice().compareTo(BigDecimal.ZERO) > 0)
            .allMatch(p -> p.getUpdatedAt().isAfter(LocalDateTime.now().minusMinutes(5)));
    });

    // Step 4: 验证API可查询最新价格
    MarketPriceResponse priceResp = dataQueryService.getMarketPrice("A4打印纸");
    assertThat(priceResp.getPriceRange().getAvg()).isBetween(30.0, 100.0);
}
```

---

## 八、集成测试执行配置

### application-integration-test.yml

```yaml
spring:
  datasource:
    url: jdbc:tc:mysql:8.0:///ilbuy_test?TC_INITSCRIPT=init-test-db.sql
  redis:
    host: ${embedded.redis.host:localhost}
    port: ${embedded.redis.port:6379}
  kafka:
    bootstrap-servers: ${embedded.kafka.brokers:localhost:9092}

nacos:
  discovery:
    server-addr: ${embedded.nacos.address:localhost:8848}
  config:
    server-addr: ${embedded.nacos.address:localhost:8848}

# 缩短超时时间加速测试
feign:
  client:
    config:
      default:
        connect-timeout: 2000
        read-timeout: 5000

sentinel:
  transport:
    dashboard: ''  # 关闭Sentinel控制台连接

logging:
  level:
    com.ilbuy: DEBUG
```

### 执行命令

```bash
# 执行集成测试（需Docker环境）
mvn verify -P integration-test -Dspring.profiles.active=integration-test

# 只执行集成测试跳过单元测试
mvn verify -P integration-test \
  -DskipUnitTests=true \
  -Dspring.profiles.active=integration-test

# 生成完整测试报告
mvn verify -P integration-test surefire-report:report
```
