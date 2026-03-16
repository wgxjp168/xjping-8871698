package com.ilbuy.gateway.filter;

import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

/**
 * B2B / B2C 场景路由过滤器
 *
 * 在 JwtAuthGlobalFilter 之后运行，读取已注入的 X-User-Role 头，
 * 判断当前请求属于哪个场景并注入 X-Scene 头，供下游服务直接使用。
 *
 * 场景判断规则：
 *   B2B — 角色包含 B2B / SUPPLIER / MANAGER / FINANCE
 *   B2C — 其他已登录用户（消费者）
 *   ANONYMOUS — 未携带 X-User-Role（匿名访问白名单路径）
 *
 * 下游服务可通过 @RequestHeader("X-Scene") 直接获取场景标识，
 * 根据场景执行差异化业务逻辑（如 B2B 最低起订量校验、B2C 优惠券应用）。
 */
@Component
@Slf4j
public class SceneRoutingFilter implements GlobalFilter, Ordered {

    /** 紧跟 JwtAuthGlobalFilter(-200) 之后运行 */
    private static final int ORDER = -199;

    public static final String HEADER_SCENE = "X-Scene";

    public static final String SCENE_B2B       = "B2B";
    public static final String SCENE_B2C       = "B2C";
    public static final String SCENE_ANONYMOUS = "ANONYMOUS";

    @Override
    public int getOrder() {
        return ORDER;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String role  = exchange.getRequest().getHeaders().getFirst(JwtAuthGlobalFilter.HEADER_USER_ROLE);
        String scene = resolveScene(role);

        log.debug("SceneRouting: role={} → scene={} path={}",
                role, scene, exchange.getRequest().getPath().value());

        // 防止客户端伪造 X-Scene 头
        ServerHttpRequest mutated = exchange.getRequest().mutate()
                .headers(h -> h.remove(HEADER_SCENE))
                .header(HEADER_SCENE, scene)
                .build();

        return chain.filter(exchange.mutate().request(mutated).build());
    }

    // ── 私有工具 ─────────────────────────────────────────────────

    /**
     * 根据用户角色确定业务场景。
     * 规则与 user-svc 的 UserRole 枚举保持一致。
     */
    private String resolveScene(String role) {
        if (role == null || role.isBlank()) {
            return SCENE_ANONYMOUS;
        }
        String upper = role.toUpperCase();
        if (upper.contains("B2B")
                || upper.contains("SUPPLIER")
                || upper.contains("MANAGER")
                || upper.contains("FINANCE")
                || upper.contains("ADMIN")) {    // ADMIN 可访问 B2B 后台功能
            return SCENE_B2B;
        }
        return SCENE_B2C;
    }
}
