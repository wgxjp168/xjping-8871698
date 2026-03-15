package com.ilbuy.l0.input.parser.platform;

import lombok.Getter;
import lombok.RequiredArgsConstructor;

import java.util.Arrays;
import java.util.Optional;

/**
 * 支持的电商平台枚举（7大平台）
 *
 * <p>用于链接输入解析时识别来源平台，
 * 决策引擎将据此选择对应数据采集策略（L3层）。
 *
 * @author ILbuy Team
 */
@Getter
@RequiredArgsConstructor
public enum EcommercePlatform {

    TAOBAO("taobao", "淘宝", new String[]{"taobao.com", "m.taobao.com"}),
    TMALL("tmall", "天猫", new String[]{"tmall.com", "detail.tmall.com", "chaoshi.detail.tmall.com"}),
    JD("jd", "京东", new String[]{"jd.com", "item.jd.com", "m.jd.com", "3.cn"}),
    PINDUODUO("pdd", "拼多多", new String[]{"pinduoduo.com", "mobile.yangkeduo.com", "p.pinduoduo.com"}),
    SUNING("suning", "苏宁", new String[]{"suning.com", "product.suning.com", "m.suning.com"}),
    AMAZON_CN("amazon", "亚马逊中国", new String[]{"amazon.cn", "www.amazon.cn"}),
    XIAOHONGSHU("xhs", "小红书", new String[]{"xiaohongshu.com", "xhslink.com", "www.xiaohongshu.com"}),
    UNKNOWN("unknown", "未知平台", new String[]{});

    private final String code;
    private final String displayName;
    private final String[] domains;

    /**
     * 根据URL主机名匹配平台
     */
    public static EcommercePlatform fromHost(String host) {
        if (host == null) return UNKNOWN;
        String lowerHost = host.toLowerCase();
        return Arrays.stream(values())
                .filter(p -> p != UNKNOWN)
                .filter(p -> Arrays.stream(p.domains)
                        .anyMatch(lowerHost::contains))
                .findFirst()
                .orElse(UNKNOWN);
    }

    /**
     * 根据 code 查找平台
     */
    public static Optional<EcommercePlatform> fromCode(String code) {
        return Arrays.stream(values())
                .filter(p -> p.code.equalsIgnoreCase(code))
                .findFirst();
    }

    public boolean isKnown() {
        return this != UNKNOWN;
    }
}
