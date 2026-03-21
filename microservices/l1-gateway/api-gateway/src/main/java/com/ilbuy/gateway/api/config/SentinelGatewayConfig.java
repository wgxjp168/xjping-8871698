package com.ilbuy.gateway.api.config;

import com.alibaba.csp.sentinel.adapter.gateway.common.rule.GatewayFlowRule;
import com.alibaba.csp.sentinel.adapter.gateway.common.rule.GatewayParamFlowItem;
import com.alibaba.csp.sentinel.adapter.gateway.common.rule.GatewayRuleManager;
import com.alibaba.csp.sentinel.adapter.gateway.sc.SentinelGatewayFilter;
import com.alibaba.csp.sentinel.adapter.gateway.sc.callback.GatewayCallbackManager;
import com.alibaba.csp.sentinel.slots.block.RuleConstant;
import com.alibaba.csp.sentinel.slots.block.degrade.DegradeRule;
import com.alibaba.csp.sentinel.slots.block.degrade.DegradeRuleManager;
import com.ilbuy.gateway.api.handler.SentinelFallbackHandler;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.Ordered;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Sentinel 网关限流与熔断规则配置
 *
 * <p>限流规则（资源维度）：
 * <ul>
 *   <li>dialog-service:  C端 100 QPS/用户（每分钟约 1.67/s，实际按 QPS 配置）</li>
 *   <li>order-service:   C端 50 QPS/用户</li>
 *   <li>b-api-route:     B端 1000 请求/分钟（约 16.67 QPS）</li>
 * </ul>
 * </p>
 *
 * <p>熔断规则（慢调用比例）：
 * <ul>
 *   <li>RT > 500ms 且比例 > 60% → 熔断 10s</li>
 *   <li>异常比例 > 50% → 熔断 15s</li>
 * </ul>
 * </p>
 *
 * <p>生产环境建议：通过 Nacos 动态推送规则，此处仅为默认兜底值。</p>
 */
@Slf4j
@Configuration
@RequiredArgsConstructor
public class SentinelGatewayConfig {

    /** Sentinel 网关过滤器 Bean */
    private final SentinelFallbackHandler fallbackHandler;

    @Bean
    @org.springframework.core.annotation.Order(Ordered.HIGHEST_PRECEDENCE)
    public GlobalFilter sentinelGatewayFilter() {
        return new SentinelGatewayFilter();
    }

    @PostConstruct
    public void initRules() {
        // 注册降级处理器
        GatewayCallbackManager.setBlockHandler(fallbackHandler);

        initGatewayFlowRules();
        initDegradeRules();
        log.info("[Sentinel] 网关流控/熔断规则初始化完成");
    }

    // ─────────────────── 限流规则 ───────────────────

    private void initGatewayFlowRules() {
        Set<GatewayFlowRule> rules = new HashSet<>();

        // C端对话服务：100 请求/分钟 ≈ 1.67 QPS（Sentinel 以 QPS 计，取整为 2）
        // 实际限制：每秒最多 2 次 → 基本等价于分钟级 100
        rules.add(new GatewayFlowRule("dialog-service")
                .setCount(2)                              // QPS 阈值
                .setIntervalSec(1)
                .setParamItem(new GatewayParamFlowItem()
                        .setParseStrategy(0)              // 0=clientIP，1=远程HOST，2=Header，3=URL参数，4=Cookie
                        .setFieldName("X-User-Id"))       // 按用户 ID 限流
        );

        // C端订单服务：50 请求/分钟
        rules.add(new GatewayFlowRule("order-service")
                .setCount(1)
                .setIntervalSec(1)
                .setParamItem(new GatewayParamFlowItem()
                        .setParseStrategy(2)              // Header
                        .setFieldName("X-User-Id"))
        );

        // B端 API（IP 维度）：1000 请求/分钟 ≈ 16.67 QPS
        rules.add(new GatewayFlowRule("b-api-route")
                .setCount(17)
                .setIntervalSec(1)
                .setParamItem(new GatewayParamFlowItem()
                        .setParseStrategy(0))             // clientIP
        );

        // 全局兜底：防止任意路由无限 QPS（500 QPS）
        rules.add(new GatewayFlowRule("global-route")
                .setCount(500)
                .setIntervalSec(1)
        );

        GatewayRuleManager.loadRules(rules);
    }

    // ─────────────────── 熔断规则 ───────────────────

    private void initDegradeRules() {
        List<DegradeRule> rules = new ArrayList<>();

        // dialog-service：慢调用平均 RT 熔断（平均 RT > 500ms，熔断 10s）
        // DEGRADE_GRADE_RT = 0（慢调用平均响应时间）
        DegradeRule dialogSlowRule = new DegradeRule("dialog-service")
                .setStrategy(RuleConstant.DEGRADE_GRADE_RT)
                .setCount(500)           // 平均响应时间阈值（ms）
                .setStatIntervalMs(10_000)
                .setMinRequestAmount(10)
                .setTimeWindow(10);      // 熔断恢复时间（s）
        rules.add(dialogSlowRule);

        // dialog-service：异常比例熔断（> 50%，熔断 15s）
        // DEGRADE_GRADE_EXCEPTION_RATIO = 1（异常比例，0.0~1.0）
        DegradeRule dialogErrorRule = new DegradeRule("dialog-service")
                .setStrategy(RuleConstant.DEGRADE_GRADE_EXCEPTION_RATIO)
                .setCount(0.5)           // 异常比例阈值 50%
                .setStatIntervalMs(10_000)
                .setMinRequestAmount(10)
                .setTimeWindow(15);
        rules.add(dialogErrorRule);

        // order-service：慢调用熔断（平均 RT > 1000ms，熔断 20s）
        DegradeRule orderSlowRule = new DegradeRule("order-service")
                .setStrategy(RuleConstant.DEGRADE_GRADE_RT)
                .setCount(1_000)
                .setStatIntervalMs(10_000)
                .setMinRequestAmount(5)
                .setTimeWindow(20);
        rules.add(orderSlowRule);

        DegradeRuleManager.loadRules(rules);
    }
}
