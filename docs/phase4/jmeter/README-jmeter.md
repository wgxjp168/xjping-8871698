# JMeter 性能测试使用说明

## 环境要求

- JMeter 5.6.2+（下载：https://jmeter.apache.org/download_jmeter.cgi）
- Java 11+
- 测试机内存 ≥ 8GB

## 文件说明

| 文件 | 说明 |
|------|------|
| `ilbuy_performance_test.jmx` | 主测试计划（可直接导入JMeter） |
| `test_users.csv` | 测试用户数据（需提前在测试环境创建这些账号） |
| `product_keywords.csv` | 商品关键词数据 |

## 使用步骤

### 1. 图形界面运行（调试）

```bash
# 启动JMeter GUI
./bin/jmeter.sh

# 打开 ilbuy_performance_test.jmx
# 修改变量：BASE_URL 改为你的测试环境地址
# 选择要运行的场景（启用/禁用 ThreadGroup）
# 点击运行
```

### 2. 命令行运行（正式压测）

```bash
# 基础运行（使用默认参数）
./bin/jmeter -n -t ilbuy_performance_test.jmx -l results/result.jtl

# 自定义参数运行
./bin/jmeter -n \
  -t ilbuy_performance_test.jmx \
  -JBASE_URL=api-test.ilbuy.com \
  -JPORT=443 \
  -JPROTOCOL=https \
  -JRAMP_UP_SECONDS=60 \
  -JTEST_DURATION_SECONDS=300 \
  -l results/result_$(date +%Y%m%d_%H%M%S).jtl \
  -e -o reports/html_report_$(date +%Y%m%d_%H%M%S)/

# 运行特定场景（通过enable/disable ThreadGroup）
./bin/jmeter -n \
  -t ilbuy_performance_test.jmx \
  -Jjmeter.reportgenerator.overall_granularity=60000 \
  -l results/procurement_test.jtl \
  -e -o reports/procurement_report/
```

### 3. 生成 HTML 报告

```bash
# 从 .jtl 文件生成报告
./bin/jmeter -g results/result.jtl -o reports/html_report/

# 查看报告
open reports/html_report/index.html
```

## 性能目标

| 接口 | 目标 QPS | P99 延迟 | 错误率 |
|------|---------|---------|-------|
| 用户登录 | 500 | ≤ 500ms | < 0.1% |
| 创建采购需求 | 200 | ≤ 1000ms | < 0.1% |
| 查询采购列表 | 1000 | ≤ 200ms | < 0.1% |
| AI匹配触发 | 100 | ≤ 2000ms | < 1% |
| 市场价格查询 | 500 | ≤ 300ms | < 0.1% |

## 注意事项

1. **压测前准备：** 确保测试环境有足够的基础数据（采购需求、供应商等）
2. **不要在生产环境压测**，除非有明确的流量录制/回放方案
3. 场景4（限流测试）默认禁用，需要时手动启用
4. 建议使用 JMeter Distributed Testing（分布式压测）进行大流量测试
5. 压测时同时监控服务器指标（CPU/内存/网络/数据库连接）
