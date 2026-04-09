# 我来购ILbuy 接口测试用例

## 概述

| 属性 | 说明 |
|------|------|
| 项目名称 | 我来购ILbuy采购平台 |
| 测试类型 | 接口测试（API Test） |
| 测试工具 | Postman / Newman / RestAssured |
| 测试环境 | 测试环境：https://api-test.ilbuy.com |
| 认证方式 | Bearer Token (JWT) |

---

## 一、认证接口（Auth API）

### TC-API-001 用户登录

| 字段 | 内容 |
|------|------|
| 测试ID | TC-API-001 |
| 接口 | POST /api/v1/auth/login |
| 测试场景 | 正常登录获取Token |

**请求：**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "test_buyer_001",
  "password": "Test@123456",
  "captchaToken": "captcha_token_xxx"
}
```

**预期响应（200 OK）：**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "accessToken": "eyJhbGciOiJIUzUxMiJ9...",
    "refreshToken": "eyJhbGciOiJIUzUxMiJ9...",
    "tokenType": "Bearer",
    "expiresIn": 7200,
    "userId": 1001,
    "username": "test_buyer_001",
    "userType": "ENTERPRISE",
    "roles": ["ROLE_BUYER"]
  }
}
```

**断言检查：**
```javascript
// Postman Tests
pm.test("响应状态码为200", () => pm.response.to.have.status(200));
pm.test("返回accessToken", () => {
    const resp = pm.response.json();
    pm.expect(resp.code).to.equal(0);
    pm.expect(resp.data.accessToken).to.be.a('string').and.not.empty;
    pm.expect(resp.data.expiresIn).to.equal(7200);
    // 保存Token供后续接口使用
    pm.environment.set("access_token", resp.data.accessToken);
    pm.environment.set("refresh_token", resp.data.refreshToken);
});
pm.test("响应时间小于500ms", () => pm.expect(pm.response.responseTime).to.be.below(500));
```

---

### TC-API-002 登录失败 - 密码错误

**请求：**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "test_buyer_001",
  "password": "WrongPassword",
  "captchaToken": "captcha_token_xxx"
}
```

**预期响应（401）：**
```json
{
  "code": 10001,
  "message": "用户名或密码错误",
  "data": null
}
```

---

### TC-API-003 Token刷新

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refreshToken": "{{refresh_token}}"
}
```

**预期：** 返回新的 accessToken，expiresIn=7200

---

## 二、采购需求接口（Procurement API）

### TC-API-010 创建B2B采购需求

```http
POST /api/v1/procurement/demands
Authorization: Bearer {{access_token}}
Content-Type: application/json

{
  "procurementType": "B2B",
  "categoryId": 1,
  "productName": "A4打印纸",
  "productSpec": "70g，500张/包，5包/箱",
  "quantity": 100,
  "unit": "箱",
  "budgetAmount": 5000.00,
  "currency": "CNY",
  "deliveryDeadline": "2024-04-20",
  "deliveryAddress": "北京市朝阳区建国路88号",
  "contactName": "张采购",
  "contactPhone": "13800138001",
  "requireTaxInvoice": true,
  "invoiceType": "SPECIAL_VAT",
  "remark": "需要发票，品牌不限"
}
```

**预期响应（201 Created）：**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "demandId": 3001,
    "orderNo": "PRO202403220001",
    "status": "MATCHING",
    "estimatedMatchTime": "2024-03-22T15:30:00",
    "message": "需求已提交，正在为您智能匹配供应商"
  }
}
```

**断言：**
```javascript
pm.test("创建成功，返回201", () => pm.response.to.have.status(201));
pm.test("返回demandId和orderNo", () => {
    const data = pm.response.json().data;
    pm.expect(data.demandId).to.be.a('number');
    pm.expect(data.orderNo).to.match(/^PRO\d{14}$/);
    pm.expect(data.status).to.equal("MATCHING");
    pm.environment.set("demand_id", data.demandId);
    pm.environment.set("order_no", data.orderNo);
});
```

---

### TC-API-011 查询采购需求详情

```http
GET /api/v1/procurement/demands/{{demand_id}}
Authorization: Bearer {{access_token}}
```

**预期响应：**
```json
{
  "code": 0,
  "data": {
    "demandId": 3001,
    "orderNo": "PRO202403220001",
    "status": "MATCHING",
    "procurementType": "B2B",
    "categoryName": "办公用品",
    "productName": "A4打印纸",
    "quantity": 100,
    "unit": "箱",
    "budgetAmount": 5000.00,
    "matchedSuppliers": [],
    "createdAt": "2024-03-22T14:00:00",
    "updatedAt": "2024-03-22T14:00:00"
  }
}
```

---

### TC-API-012 采购需求分页列表

```http
GET /api/v1/procurement/demands?page=0&size=10&status=MATCHING&sortBy=createdAt&direction=DESC
Authorization: Bearer {{access_token}}
```

**断言：**
```javascript
pm.test("分页结构正确", () => {
    const data = pm.response.json().data;
    pm.expect(data.content).to.be.an('array');
    pm.expect(data.totalElements).to.be.a('number');
    pm.expect(data.totalPages).to.be.a('number');
    pm.expect(data.size).to.equal(10);
    pm.expect(data.number).to.equal(0);
});
```

---

### TC-API-013 取消采购需求

```http
PUT /api/v1/procurement/demands/{{demand_id}}/cancel
Authorization: Bearer {{access_token}}
Content-Type: application/json

{
  "reason": "预算调整，暂时取消"
}
```

**预期：** 状态变更为 CANCELLED，返回 200

---

## 三、AI匹配接口（AI Matching API）

### TC-API-020 触发AI智能匹配

```http
POST /api/v1/matching/trigger
Authorization: Bearer {{access_token}}
Content-Type: application/json

{
  "demandId": {{demand_id}},
  "matchMode": "AUTO",
  "maxSuppliers": 5
}
```

**预期响应：**
```json
{
  "code": 0,
  "data": {
    "matchTaskId": "match_task_20240322_001",
    "status": "PROCESSING",
    "estimatedSeconds": 30,
    "webhookUrl": "/api/v1/matching/result/match_task_20240322_001"
  }
}
```

---

### TC-API-021 查询匹配结果

```http
GET /api/v1/matching/result/{{match_task_id}}
Authorization: Bearer {{access_token}}
```

**预期响应：**
```json
{
  "code": 0,
  "data": {
    "matchTaskId": "match_task_20240322_001",
    "status": "COMPLETED",
    "matchedSuppliers": [
      {
        "supplierId": 5001,
        "supplierName": "北京文具联盟有限公司",
        "matchScore": 92.5,
        "matchReasons": ["历史成交记录匹配", "品类专业度高", "响应速度快"],
        "estimatedPrice": 4800.00,
        "deliveryDays": 3,
        "creditRating": "AAA"
      }
    ],
    "aiAnalysis": "该需求属于标准办公耗材采购，推荐优先联系北京文具联盟...",
    "completedAt": "2024-03-22T14:00:30"
  }
}
```

---

### TC-API-022 AI意图解析 — 文字输入（正常）

| 字段 | 内容 |
|------|------|
| 测试ID | TC-API-022 |
| 接口 | POST /api/v1/ai/intent/parse |
| 测试场景 | 文字输入正常解析采购意图 |

**请求：**
```http
POST /api/v1/ai/intent/parse
Authorization: Bearer {{access_token}}
Content-Type: application/json

{
  "input_type": "text",
  "text": "我需要采购100台联想笔记本，预算50万元"
}
```

**预期响应（200 OK）：**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "productName": "联想笔记本",
    "category": "电子设备",
    "quantity": 100,
    "budgetAmount": 500000,
    "procurementType": "B2B",
    "inputType": "text",
    "contextAware": false,
    "note": "本接口为无状态设计，不保留上下文，每次请求独立处理。"
  }
}
```

> **说明：** `input_type` 默认为 `text`，可省略。每次请求独立处理，不保留历史上下文。

---

### TC-API-023 AI意图解析 — 语音输入（ASR 转写）

| 字段 | 内容 |
|------|------|
| 测试ID | TC-API-023 |
| 接口 | POST /api/v1/ai/intent/parse |
| 测试场景 | 语音输入经 ASR 引擎转写后完成意图解析 |

**请求：**
```http
POST /api/v1/ai/intent/parse
Authorization: Bearer {{access_token}}
Content-Type: application/json

{
  "input_type": "voice",
  "voice_url": "https://oss.ilbuy.com/voice/req_001.wav",
  "language": "zh-CN"
}
```

或通过 Base64 上传音频：
```json
{
  "input_type": "voice",
  "voice_base64": "<base64_encoded_pcm_or_wav>",
  "language": "zh-CN"
}
```

**预期响应（200 OK）：**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "productName": "联想笔记本",
    "category": "IT设备",
    "quantity": 100,
    "budgetAmount": 500000,
    "procurementType": "B2B",
    "inputType": "voice",
    "contextAware": false,
    "asr": {
      "engine": "whisper",
      "transcript": "我需要采购100台联想笔记本，预算50万元",
      "language": "zh-CN",
      "activeEngine": "whisper",
      "engines": {
        "whisper": "openai-whisper 本地离线模型（最高精度）",
        "google_stt": "Google Cloud Speech-to-Text（需联网）",
        "stub": "模拟转写（用于测试，需安装 whisper 或 SpeechRecognition）"
      }
    }
  }
}
```

**ASR 引擎优先级：**

| 优先级 | 引擎 | 安装方式 | 特点 |
|--------|------|----------|------|
| 1 | `whisper` | `pip install openai-whisper` | 本地离线，支持中文，最高精度 |
| 2 | `google_stt` | `pip install SpeechRecognition` | 需联网，调用 Google STT API |
| 3 | `stub` | 无需安装 | 测试用模拟转写，非生产环境 |

> **说明：** ASR 引擎自动检测，优先使用已安装的最高优先级引擎。`asr.engine` 字段标注本次使用的实际引擎。

---

### TC-API-024 AI意图解析 — 图片输入（无法准确解释商品）

| 字段 | 内容 |
|------|------|
| 测试ID | TC-API-024 |
| 接口 | POST /api/v1/ai/intent/parse |
| 测试场景 | 上传图片无法准确提取商品采购要素 |

**请求：**
```http
POST /api/v1/ai/intent/parse
Authorization: Bearer {{access_token}}
Content-Type: application/json

{
  "input_type": "image",
  "image_url": "https://oss.ilbuy.com/images/product_photo_001.jpg"
}
```

**预期响应（422 Unprocessable Entity）：**
```json
{
  "code": 42202,
  "message": "图片输入无法准确解释商品：AI 视觉模块未接入，无法从图片中自动提取商品名称、型号、规格等采购要素。",
  "data": {
    "inputType": "image",
    "supported": false,
    "suggestion": "请用文字描述商品名称、规格和数量，或提供商品编号/型号。",
    "contextAware": false
  }
}
```

> **局限说明：** 当前 AI 服务不具备图像识别（CV）能力。即使上传清晰的商品图片，系统也无法自动识别商品名称、品牌、规格参数等采购关键要素。请以文字形式补充描述。

---

### TC-API-025 AI意图解析 — 链接输入（无法解释商品）

| 字段 | 内容 |
|------|------|
| 测试ID | TC-API-025 |
| 接口 | POST /api/v1/ai/intent/parse |
| 测试场景 | 提供商品链接无法自动提取采购信息 |

**请求：**
```http
POST /api/v1/ai/intent/parse
Authorization: Bearer {{access_token}}
Content-Type: application/json

{
  "input_type": "link",
  "url": "https://item.jd.com/100012043978.html"
}
```

**预期响应（422 Unprocessable Entity）：**
```json
{
  "code": 42203,
  "message": "链接输入无法解释商品：系统不支持抓取外部链接内容，无法从商品页面 URL 中自动提取采购信息。",
  "data": {
    "inputType": "link",
    "supported": false,
    "suggestion": "请复制商品名称和规格，以文字形式提交采购需求。",
    "contextAware": false
  }
}
```

> **局限说明：** 系统不具备网页内容抓取（爬虫）能力，无法解析京东、淘宝、1688 等电商平台的商品链接。请手动复制商品名称、型号和规格后以文字提交。

---

### TC-API-026 AI意图解析 — 无上下文理解（验证无状态）

| 字段 | 内容 |
|------|------|
| 测试ID | TC-API-026 |
| 接口 | POST /api/v1/ai/intent/parse |
| 测试场景 | 验证系统不保留对话上下文 |

**第一次请求：**
```http
POST /api/v1/ai/intent/parse
Authorization: Bearer {{access_token}}
Content-Type: application/json

{ "input_type": "text", "text": "我要买联想笔记本" }
```

**第二次请求（省略商品名，期望系统记住）：**
```http
POST /api/v1/ai/intent/parse
Authorization: Bearer {{access_token}}
Content-Type: application/json

{ "input_type": "text", "text": "再来100台，预算加到80万" }
```

**预期结果：**
- 第二次请求将"再来100台"解析为独立需求，无法关联第一次的"联想笔记本"
- 响应中 `contextAware: false` 明确标注无上下文

> **局限说明：** 本接口为无状态（Stateless）设计，每次调用独立处理，不维护会话历史。如需多轮对话式采购引导，需由客户端拼接上下文后一次性提交完整描述。

---

## 多模态输入能力矩阵

| 输入类型 | 支持状态 | 错误码 | 说明 |
|----------|----------|--------|------|
| `text`（文字）| ✅ 支持 | — | 推荐方式，支持中文自然语言描述 |
| `voice`（语音）| ✅ 支持（ASR）| 42201* | 自动转写：whisper → google_stt → stub |
| `image`（图片）| ❌ 不支持 | 42202 | 未集成 CV 模块，无法准确识别商品 |
| `link`（链接）| ❌ 不支持 | 42203 | 不支持爬取外部 URL 内容 |
| 上下文记忆 | ❌ 无状态 | — | 每次请求独立处理，不保留历史 |

> *42201 仅在 ASR 转写失败（无音频数据且无 URL）时返回。正常情况下语音输入返回 200。

---

## 四、询价报价接口（Inquiry API）

### TC-API-030 发起询价

```http
POST /api/v1/inquiry
Authorization: Bearer {{access_token}}
Content-Type: application/json

{
  "demandId": {{demand_id}},
  "supplierIds": [5001, 5002, 5003],
  "inquiryDeadline": "2024-03-25T18:00:00",
  "message": "请按需求规格报价，含增值税专用发票"
}
```

**预期：** 返回 inquiryId，状态 SENT

---

### TC-API-031 供应商提交报价

```http
POST /api/v1/inquiry/{{inquiry_id}}/quotes
Authorization: Bearer {{supplier_access_token}}
Content-Type: application/json

{
  "unitPrice": 46.50,
  "currency": "CNY",
  "totalAmount": 4650.00,
  "taxRate": 0.13,
  "taxIncluded": false,
  "deliveryDays": 2,
  "validDays": 7,
  "remark": "现货供应，当日可发货",
  "attachments": ["quote_detail_001.pdf"]
}
```

**预期：** 返回 quoteId，状态 SUBMITTED；买家收到通知

---

### TC-API-032 接受报价

```http
PUT /api/v1/inquiry/{{inquiry_id}}/quotes/{{quote_id}}/accept
Authorization: Bearer {{access_token}}
```

**预期：** 自动创建订单，返回 orderId

---

## 五、订单接口（Order API）

### TC-API-040 查询订单详情

```http
GET /api/v1/orders/{{order_id}}
Authorization: Bearer {{access_token}}
```

**预期响应字段验证：**
```javascript
pm.test("订单字段完整", () => {
    const order = pm.response.json().data;
    pm.expect(order).to.have.property('orderId');
    pm.expect(order).to.have.property('orderNo');
    pm.expect(order).to.have.property('status');
    pm.expect(order).to.have.property('totalAmount');
    pm.expect(order).to.have.property('taxAmount');
    pm.expect(order).to.have.property('buyerInfo');
    pm.expect(order).to.have.property('supplierInfo');
    pm.expect(order).to.have.property('items');
    pm.expect(order.items).to.be.an('array').with.length.above(0);
});
```

---

### TC-API-041 订单确认收货

```http
PUT /api/v1/orders/{{order_id}}/confirm-receipt
Authorization: Bearer {{access_token}}
Content-Type: application/json

{
  "receiptTime": "2024-03-25T10:00:00",
  "quantity": 100,
  "qualityOk": true,
  "remark": "货物完好，数量正确"
}
```

---

## 六、供应商接口（Supplier API）

### TC-API-050 供应商入驻申请

```http
POST /api/v1/suppliers/register
Content-Type: application/json

{
  "companyName": "北京测试供应商有限公司",
  "creditCode": "91110108MA01ABCD12",
  "businessLicense": "base64_encoded_image...",
  "contactName": "李供应",
  "contactPhone": "13900139001",
  "contactEmail": "supply@testcorp.com",
  "mainCategories": [1, 2, 3],
  "annualSales": 5000000.00,
  "bankName": "中国银行北京分行",
  "bankAccount": "620000123456789",
  "bankAccountName": "北京测试供应商有限公司"
}
```

**预期：** 返回 supplierId，status=REVIEWING；邮件通知

---

### TC-API-051 供应商价格目录上传

```http
POST /api/v1/suppliers/{{supplier_id}}/catalog
Authorization: Bearer {{supplier_access_token}}
Content-Type: multipart/form-data

file: [price_catalog.xlsx]
categoryId: 1
effectiveDate: 2024-03-22
expiryDate: 2024-06-30
```

---

## 七、数据查询接口（Data API）

### TC-API-060 市场价格查询

```http
GET /api/v1/data/market-price?keyword=A4打印纸&categoryId=1&sources=JD,TAOBAO,PDD
Authorization: Bearer {{access_token}}
```

**预期：**
```json
{
  "code": 0,
  "data": {
    "keyword": "A4打印纸",
    "priceRange": {
      "min": 38.90,
      "max": 58.00,
      "avg": 46.50,
      "median": 45.00
    },
    "sources": [
      {"source": "JD", "price": 48.00, "updatedAt": "2024-03-22T12:00:00"},
      {"source": "TAOBAO", "price": 43.50, "updatedAt": "2024-03-22T11:30:00"},
      {"source": "PDD", "price": 38.90, "updatedAt": "2024-03-22T11:00:00"}
    ],
    "trend": "STABLE"
  }
}
```

---

## 八、错误场景测试

### TC-API-070 未认证访问受保护接口

```http
GET /api/v1/procurement/demands/3001
# 不携带 Authorization header
```

**预期：** 401 Unauthorized
```json
{"code": 10002, "message": "未认证，请先登录"}
```

---

### TC-API-071 参数校验失败

```http
POST /api/v1/procurement/demands
Authorization: Bearer {{access_token}}
Content-Type: application/json

{
  "procurementType": "B2B",
  "quantity": -1,
  "budgetAmount": 0
}
```

**预期：** 400 Bad Request
```json
{
  "code": 10003,
  "message": "参数校验失败",
  "errors": [
    {"field": "productName", "message": "商品名称不能为空"},
    {"field": "quantity", "message": "数量必须大于0"},
    {"field": "budgetAmount", "message": "预算金额必须大于0"}
  ]
}
```

---

### TC-API-072 接口限流测试

```javascript
// 1秒内发送超过限流阈值的请求
const requests = [];
for (let i = 0; i < 110; i++) {
    requests.push(pm.sendRequest({
        url: pm.environment.get("base_url") + "/api/v1/procurement/demands",
        method: "GET",
        header: { "Authorization": "Bearer " + pm.environment.get("access_token") }
    }));
}
// 期望第100+次请求返回 429 Too Many Requests
```

---

## 九、Newman批量执行配置

```bash
# 安装 Newman
npm install -g newman newman-reporter-html

# 执行测试集合
newman run ilbuy_api_tests.postman_collection.json \
  --environment ilbuy_test_env.postman_environment.json \
  --reporters cli,html \
  --reporter-html-export reports/api-test-report.html \
  --delay-request 200 \
  --timeout-request 30000 \
  --bail

# 生成详细报告
newman run ilbuy_api_tests.postman_collection.json \
  -e ilbuy_test_env.postman_environment.json \
  -r htmlextra \
  --reporter-htmlextra-export reports/api-test-detailed-report.html
```
