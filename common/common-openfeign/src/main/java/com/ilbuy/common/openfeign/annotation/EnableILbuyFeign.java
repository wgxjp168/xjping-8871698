package com.ilbuy.common.openfeign.annotation;

import com.ilbuy.common.openfeign.config.FeignConfig;
import org.springframework.cloud.openfeign.EnableFeignClients;
import org.springframework.context.annotation.Import;

import java.lang.annotation.*;

/**
 * 启用 ILbuy Feign 客户端（一键集成）
 *
 * <p>各微服务在启动类上添加此注解即可，无需重复配置 Feign：</p>
 * <pre>{@code
 * @SpringBootApplication
 * @EnableILbuyFeign(basePackages = "com.ilbuy.l5.client")
 * public class L5Application { ... }
 * }</pre>
 */
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Documented
@EnableFeignClients
@Import(FeignConfig.class)
public @interface EnableILbuyFeign {

    /**
     * Feign Client 扫描包路径
     */
    String[] basePackages() default {};

    /**
     * Feign Client 扫描包类（通过类指定包）
     */
    Class<?>[] basePackageClasses() default {};
}
