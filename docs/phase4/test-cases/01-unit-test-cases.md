# 我来购ILbuy 单元测试用例

## 概述

| 属性 | 说明 |
|------|------|
| 项目名称 | 我来购ILbuy采购平台 |
| 测试类型 | 单元测试（Unit Test） |
| 测试框架 | JUnit5 + Mockito + AssertJ |
| 覆盖目标 | 核心业务逻辑类，覆盖率 ≥ 80% |
| 执行方式 | Maven: `mvn test -pl <module>` |

---

## 一、用户服务（user-service）单元测试

### TC-UT-001 用户注册 - 正常流程

| 字段 | 内容 |
|------|------|
| 测试ID | TC-UT-001 |
| 测试模块 | UserService.register() |
| 测试场景 | 企业用户正常注册 |
| 前置条件 | 数据库无同名账号，邮箱未被注册 |

**测试代码示例：**
```java
@Test
@DisplayName("TC-UT-001: 企业用户正常注册")
void testRegisterEnterpriseUser_Success() {
    // Given
    RegisterRequest req = RegisterRequest.builder()
        .username("test_corp_001")
        .password("Abc@123456")
        .email("contact@testcorp.com")
        .userType(UserType.ENTERPRISE)
        .companyName("测试企业有限公司")
        .creditCode("91110108MA01234567")
        .build();
    when(userRepository.existsByUsername("test_corp_001")).thenReturn(false);
    when(userRepository.existsByEmail("contact@testcorp.com")).thenReturn(false);
    when(userRepository.save(any(User.class))).thenAnswer(inv -> {
        User u = inv.getArgument(0);
        u.setId(1001L);
        return u;
    });

    // When
    RegisterResponse resp = userService.register(req);

    // Then
    assertThat(resp.getUserId()).isEqualTo(1001L);
    assertThat(resp.getStatus()).isEqualTo("PENDING_VERIFY");
    verify(emailService, times(1)).sendVerifyEmail("contact@testcorp.com");
    verify(auditLogService, times(1)).log(eq("USER_REGISTER"), any());
}
```

**预期结果：**
- 返回 userId=1001，status=PENDING_VERIFY
- 发送验证邮件 1 次
- 写入审计日志 1 条

---

### TC-UT-002 用户注册 - 用户名重复

| 字段 | 内容 |
|------|------|
| 测试ID | TC-UT-002 |
| 测试模块 | UserService.register() |
| 测试场景 | 用户名已存在，抛出业务异常 |

```java
@Test
@DisplayName("TC-UT-002: 用户名重复注册应抛出异常")
void testRegister_DuplicateUsername_ThrowsException() {
    // Given
    RegisterRequest req = buildRegisterRequest("existing_user");
    when(userRepository.existsByUsername("existing_user")).thenReturn(true);

    // When & Then
    assertThatThrownBy(() -> userService.register(req))
        .isInstanceOf(BizException.class)
        .hasFieldOrPropertyWithValue("code", "USER_ALREADY_EXISTS")
        .hasMessageContaining("用户名已存在");
    verify(userRepository, never()).save(any());
}
```

**预期结果：**
- 抛出 BizException，错误码 USER_ALREADY_EXISTS
- repository.save() 不被调用

---

### TC-UT-003 密码加密验证

| 字段 | 内容 |
|------|------|
| 测试ID | TC-UT-003 |
| 测试模块 | PasswordEncoder |
| 测试场景 | BCrypt 密码加密与验证 |

```java
@Test
@DisplayName("TC-UT-003: BCrypt密码加密验证")
void testPasswordEncoding() {
    String rawPassword = "Abc@123456";
    String encoded = passwordEncoder.encode(rawPassword);

    assertThat(encoded).isNotEqualTo(rawPassword);
    assertThat(encoded).startsWith("$2a$");
    assertThat(passwordEncoder.matches(rawPassword, encoded)).isTrue();
    assertThat(passwordEncoder.matches("wrong_pass", encoded)).isFalse();
}
```

---

### TC-UT-004 JWT Token 生成与解析

```java
@Test
@DisplayName("TC-UT-004: JWT Token生成与解析")
void testJwtTokenGenerateAndParse() {
    UserDetails userDetails = buildUserDetails(1001L, "test_user", "ROLE_BUYER");

    String token = jwtTokenProvider.generateToken(userDetails);

    assertThat(token).isNotBlank();
    assertThat(jwtTokenProvider.validateToken(token)).isTrue();
    assertThat(jwtTokenProvider.getUserIdFromToken(token)).isEqualTo(1001L);
    assertThat(jwtTokenProvider.getRolesFromToken(token)).contains("ROLE_BUYER");

    // Token过期测试
    String expiredToken = buildExpiredToken(userDetails);
    assertThat(jwtTokenProvider.validateToken(expiredToken)).isFalse();
}
```

---

## 二、采购单服务（procurement-service）单元测试

### TC-UT-010 创建采购需求 - B2B企业场景

```java
@Test
@DisplayName("TC-UT-010: B2B企业采购需求创建")
void testCreateProcurementB2B_Success() {
    // Given
    ProcurementCreateRequest req = ProcurementCreateRequest.builder()
        .procurementType(ProcurementType.B2B)
        .enterpriseId(2001L)
        .categoryId(1L)           // 办公用品
        .productName("A4打印纸")
        .quantity(1000)
        .unit("箱")
        .budgetAmount(new BigDecimal("50000.00"))
        .currency("CNY")
        .deliveryDeadline(LocalDate.now().plusDays(15))
        .deliveryAddress("北京市朝阳区某某路1号")
        .contactName("张采购")
        .contactPhone("13800138000")
        .build();

    when(enterpriseService.getEnterprise(2001L)).thenReturn(buildEnterprise(2001L));
    when(categoryService.getCategory(1L)).thenReturn(buildCategory(1L, "办公用品"));
    when(procurementRepository.save(any())).thenAnswer(inv -> {
        Procurement p = inv.getArgument(0);
        p.setId(3001L);
        p.setOrderNo("PRO202403220001");
        return p;
    });

    // When
    ProcurementCreateResponse resp = procurementService.create(req);

    // Then
    assertThat(resp.getProcurementId()).isEqualTo(3001L);
    assertThat(resp.getOrderNo()).matches("PRO\\d{14}");
    assertThat(resp.getStatus()).isEqualTo("MATCHING");
    verify(aiMatchingService, times(1)).triggerMatching(3001L);
    verify(notificationService, times(1)).notifyCreate(any());
}
```

---

### TC-UT-011 采购需求状态机流转

```java
@ParameterizedTest
@DisplayName("TC-UT-011: 采购需求状态机合法流转")
@CsvSource({
    "DRAFT, SUBMITTED, true",
    "SUBMITTED, MATCHING, true",
    "MATCHING, QUOTED, true",
    "QUOTED, NEGOTIATING, true",
    "NEGOTIATING, CONFIRMED, true",
    "CONFIRMED, COMPLETED, true",
    "DRAFT, COMPLETED, false",    // 非法流转
    "COMPLETED, DRAFT, false",    // 非法流转
    "CANCELLED, SUBMITTED, false" // 非法流转
})
void testProcurementStatusTransition(String fromStatus, String toStatus, boolean expected) {
    ProcurementStatus from = ProcurementStatus.valueOf(fromStatus);
    ProcurementStatus to = ProcurementStatus.valueOf(toStatus);

    boolean actual = procurementStateMachine.canTransit(from, to);
    assertThat(actual).isEqualTo(expected);
}
```

---

### TC-UT-012 预算校验

```java
@Test
@DisplayName("TC-UT-012: 采购预算超出企业限额应拒绝")
void testBudgetExceedsLimit_ThrowsException() {
    Enterprise enterprise = buildEnterprise(2001L);
    enterprise.setSingleOrderLimit(new BigDecimal("100000.00"));

    ProcurementCreateRequest req = buildRequest(new BigDecimal("150000.00")); // 超额
    when(enterpriseService.getEnterprise(any())).thenReturn(enterprise);

    assertThatThrownBy(() -> procurementService.create(req))
        .isInstanceOf(BizException.class)
        .hasFieldOrPropertyWithValue("code", "BUDGET_EXCEEDS_LIMIT");
}
```

---

## 三、AI匹配服务（ai-matching-service）单元测试

### TC-UT-020 供应商匹配评分算法

```java
@Test
@DisplayName("TC-UT-020: 供应商匹配评分计算")
void testSupplierMatchingScore() {
    ProcurementDemand demand = buildDemand("A4打印纸", 1000, "箱", 50000.0);

    List<Supplier> suppliers = Arrays.asList(
        buildSupplier("供应商A", 4.8, 95.0, 10, true),   // 高评分，高履约，近距离，有资质
        buildSupplier("供应商B", 4.2, 88.0, 50, true),   // 中等
        buildSupplier("供应商C", 3.5, 75.0, 200, false)  // 低评分，远距离，无资质
    );

    List<MatchResult> results = matchingEngine.match(demand, suppliers);

    assertThat(results).hasSize(3);
    assertThat(results.get(0).getSupplierName()).isEqualTo("供应商A");
    assertThat(results.get(0).getScore()).isGreaterThan(results.get(1).getScore());
    assertThat(results.get(1).getScore()).isGreaterThan(results.get(2).getScore());
    assertThat(results.get(0).getScore()).isBetween(0.0, 100.0);
}
```

---

### TC-UT-021 LLM调用超时处理

```java
@Test
@DisplayName("TC-UT-021: LLM调用超时应触发降级")
void testLlmCallTimeout_TriggersFallback() {
    when(llmClient.analyze(any())).thenThrow(new TimeoutException("LLM调用超时"));

    ProcurementAnalysisResult result = aiMatchingService.analyzeWithFallback(buildDemand());

    // 降级应使用规则引擎结果
    assertThat(result.getSource()).isEqualTo("RULE_ENGINE_FALLBACK");
    assertThat(result.getRecommendations()).isNotEmpty();
    verify(alertService, times(1)).sendLlmTimeoutAlert();
}
```

---

## 四、询价服务（inquiry-service）单元测试

### TC-UT-030 报价单创建与有效期校验

```java
@Test
@DisplayName("TC-UT-030: 报价单有效期校验")
void testQuoteExpiry() {
    Quote quote = Quote.builder()
        .id(4001L)
        .validUntil(LocalDateTime.now().minusHours(1)) // 已过期
        .status(QuoteStatus.ACTIVE)
        .build();

    when(quoteRepository.findById(4001L)).thenReturn(Optional.of(quote));

    assertThatThrownBy(() -> inquiryService.acceptQuote(4001L, buildAcceptRequest()))
        .isInstanceOf(BizException.class)
        .hasFieldOrPropertyWithValue("code", "QUOTE_EXPIRED");
}
```

---

## 五、订单服务（order-service）单元测试

### TC-UT-040 订单金额计算

```java
@Test
@DisplayName("TC-UT-040: 订单含税金额计算（13%增值税）")
void testOrderAmountCalculation() {
    OrderItem item1 = buildItem("A4纸", 100, new BigDecimal("48.00"));
    OrderItem item2 = buildItem("碳粉盒", 10, new BigDecimal("280.00"));

    Order order = orderService.calculateAmount(Arrays.asList(item1, item2));

    // 不含税：100*48 + 10*280 = 7600
    assertThat(order.getSubtotal()).isEqualByComparingTo("7600.00");
    // 增值税：7600 * 0.13 = 988
    assertThat(order.getTaxAmount()).isEqualByComparingTo("988.00");
    // 含税合计：8588
    assertThat(order.getTotalAmount()).isEqualByComparingTo("8588.00");
}
```

---

### TC-UT-041 并发下单防重复提交

```java
@Test
@DisplayName("TC-UT-041: 并发下单幂等性验证")
void testConcurrentOrderIdempotency() throws InterruptedException {
    String idempotencyKey = "order_idem_20240322_001";
    OrderCreateRequest req = buildOrderRequest();
    req.setIdempotencyKey(idempotencyKey);

    // 模拟两个并发请求使用相同幂等Key
    when(redisLock.tryLock("order:idem:" + idempotencyKey, 30)).thenReturn(true, false);
    when(orderRepository.existsByIdempotencyKey(idempotencyKey)).thenReturn(false, true);

    OrderCreateResponse resp1 = orderService.createOrder(req);
    OrderCreateResponse resp2 = orderService.createOrder(req);

    assertThat(resp1.getOrderId()).isNotNull();
    // 第二次请求应返回第一次的结果（幂等）
    assertThat(resp2.getOrderId()).isEqualTo(resp1.getOrderId());
    // 实际保存只发生一次
    verify(orderRepository, times(1)).save(any());
}
```

---

## 六、数据采集服务（data-collector-service）单元测试

### TC-UT-050 价格数据解析

```java
@Test
@DisplayName("TC-UT-050: 京东价格数据HTML解析")
void testJdPriceParsing() {
    String html = loadTestResource("jd_product_page.html");

    ProductPrice price = jdParser.parse(html);

    assertThat(price.getProductId()).isNotBlank();
    assertThat(price.getPrice()).isPositive();
    assertThat(price.getOriginalPrice()).isGreaterThanOrEqualTo(price.getPrice());
    assertThat(price.getUpdateTime()).isNotNull();
    assertThat(price.getSource()).isEqualTo("JD");
}
```

---

### TC-UT-051 反爬虫重试机制

```java
@Test
@DisplayName("TC-UT-051: 遭遇403应触发代理切换重试")
void testAntiCrawlerRetry() {
    // 第1、2次返回403，第3次成功
    when(httpClient.get(anyString()))
        .thenThrow(new HttpStatusException(403, "Forbidden"))
        .thenThrow(new HttpStatusException(403, "Forbidden"))
        .thenReturn(buildSuccessResponse());

    when(proxyPool.getProxy()).thenReturn(buildProxy());

    String result = dataCollector.fetchWithRetry("https://example.com/product/123");

    assertThat(result).isNotBlank();
    verify(proxyPool, times(2)).getProxy(); // 切换代理2次
    verify(httpClient, times(3)).get(any()); // 重试3次
}
```

---

## 七、测试执行配置

### Maven Surefire 配置（pom.xml）

```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-surefire-plugin</artifactId>
    <version>3.1.2</version>
    <configuration>
        <parallel>methods</parallel>
        <threadCount>4</threadCount>
        <includes>
            <include>**/*Test.java</include>
            <include>**/*Tests.java</include>
            <include>**/*TestCase.java</include>
        </includes>
        <excludes>
            <exclude>**/*IntegrationTest.java</exclude>
        </excludes>
        <systemPropertyVariables>
            <spring.profiles.active>test</spring.profiles.active>
        </systemPropertyVariables>
    </configuration>
</plugin>
```

### 测试覆盖率检查（JaCoCo）

```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.10</version>
    <executions>
        <execution>
            <goals><goal>prepare-agent</goal></goals>
        </execution>
        <execution>
            <id>report</id>
            <phase>test</phase>
            <goals><goal>report</goal></goals>
        </execution>
        <execution>
            <id>check</id>
            <goals><goal>check</goal></goals>
            <configuration>
                <rules>
                    <rule>
                        <element>BUNDLE</element>
                        <limits>
                            <limit>
                                <counter>LINE</counter>
                                <value>COVEREDRATIO</value>
                                <minimum>0.80</minimum>
                            </limit>
                            <limit>
                                <counter>BRANCH</counter>
                                <value>COVEREDRATIO</value>
                                <minimum>0.70</minimum>
                            </limit>
                        </limits>
                    </rule>
                </rules>
            </configuration>
        </execution>
    </executions>
</plugin>
```

### 执行命令

```bash
# 执行所有单元测试
mvn test -Dspring.profiles.active=test

# 生成覆盖率报告
mvn verify -Dspring.profiles.active=test

# 查看报告（各模块）
open target/site/jacoco/index.html
```
