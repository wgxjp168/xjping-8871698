package com.ilbuy.l0.input.parser.platform;

import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.URISyntaxException;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 电商平台URL解析器
 *
 * <p>支持7大主流平台URL解析，提取：
 * <ul>
 *   <li>平台标识 ({@link EcommercePlatform})</li>
 *   <li>平台内商品ID</li>
 *   <li>标准化URL（去除UTM追踪参数）</li>
 * </ul>
 *
 * <p>各平台URL规则：
 * <pre>
 * 淘宝/天猫: item.taobao.com/item.htm?id=xxx
 *            detail.tmall.com/item.htm?id=xxx
 * 京东:      item.jd.com/{skuId}.html
 *            3.cn/{shortCode}（短链，需HTTP跟随跳转）
 * 拼多多:    mobile.yangkeduo.com/goods.html?goods_id=xxx
 *            pinduoduo.com/goods/detail.html?goods_id=xxx
 * 苏宁:      product.suning.com/{catalogCode}/{productCode}.html
 * 亚马逊中国: amazon.cn/dp/{ASIN}/
 *             amazon.cn/gp/product/{ASIN}/
 * 小红书:    xiaohongshu.com/explore/{noteId}
 *            xiaohongshu.com/goods-detail/{goodsId}
 *            xhslink.com/{shortCode}（短链）
 * </pre>
 *
 * @author ILbuy Team
 */
@Slf4j
@Component
public class PlatformUrlParser {

    // 京东商品ID: item.jd.com/100012345.html 或 jd.com/product/123456.html
    private static final Pattern JD_ITEM_PATTERN =
            Pattern.compile("(?:item\\.jd\\.com|jd\\.com/product)/([0-9]+)\\.html");

    // 淘宝/天猫商品ID（Query参数）
    private static final Pattern TAOBAO_ID_PATTERN =
            Pattern.compile("[?&]id=([0-9]+)");

    // 拼多多商品ID
    private static final Pattern PDD_GOODS_PATTERN =
            Pattern.compile("[?&]goods_id=([0-9]+)");

    // 苏宁商品ID: product.suning.com/catalogCode/productCode.html
    private static final Pattern SUNING_PATTERN =
            Pattern.compile("suning\\.com/([0-9A-Za-z]+)/([0-9A-Za-z]+)\\.html");

    // 亚马逊中国ASIN: amazon.cn/dp/B08N5WRWNW 或 /gp/product/ASIN
    private static final Pattern AMAZON_ASIN_PATTERN =
            Pattern.compile("amazon\\.cn/(?:dp|gp/product)/([A-Z0-9]{10})");

    // 小红书笔记/商品ID
    private static final Pattern XHS_NOTE_PATTERN =
            Pattern.compile("xiaohongshu\\.com/(?:explore|goods-detail)/([a-zA-Z0-9]+)");

    // 需要剔除的追踪参数（各平台通用）
    private static final String[] TRACKING_PARAMS = {
            "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
            "spm", "scm", "pvid", "tracelog", "activity_id", "ali_trackid",
            "jd_pop", "abt", "cu", "jdSrc", "mktsid", "mkttid",
            "from", "ch", "pid", "ref", "share_token"
    };

    /**
     * 解析电商平台URL
     *
     * @param rawUrl 原始URL
     * @return 解析结果，包含平台、商品ID、标准化URL
     */
    public ParseResult parse(String rawUrl) {
        if (StringUtils.isBlank(rawUrl)) {
            return ParseResult.failed("URL为空");
        }

        // 补全协议头
        String url = rawUrl.trim();
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            url = "https://" + url;
        }

        URI uri;
        try {
            uri = new URI(url);
        } catch (URISyntaxException e) {
            log.warn("[PlatformUrlParser] 非法URL: {}", rawUrl);
            return ParseResult.failed("URL格式不合法: " + e.getMessage());
        }

        String host = uri.getHost();
        EcommercePlatform platform = EcommercePlatform.fromHost(host);

        String productId = extractProductId(platform, url, uri);
        String normalizedUrl = buildNormalizedUrl(platform, uri, productId, url);

        return ParseResult.builder()
                .platform(platform)
                .productId(productId)
                .normalizedUrl(normalizedUrl)
                .originalUrl(rawUrl)
                .success(platform.isKnown())
                .build();
    }

    // ================== 各平台商品ID提取 ==================

    private String extractProductId(EcommercePlatform platform, String url, URI uri) {
        return switch (platform) {
            case TAOBAO, TMALL -> extractByPattern(TAOBAO_ID_PATTERN, url, 1);
            case JD             -> extractByPattern(JD_ITEM_PATTERN, url, 1);
            case PINDUODUO      -> extractByPattern(PDD_GOODS_PATTERN, url, 1);
            case SUNING         -> extractSuningProductId(url);
            case AMAZON_CN      -> extractByPattern(AMAZON_ASIN_PATTERN, url, 1);
            case XIAOHONGSHU    -> extractByPattern(XHS_NOTE_PATTERN, url, 1);
            default             -> null;
        };
    }

    private String extractByPattern(Pattern pattern, String url, int group) {
        Matcher m = pattern.matcher(url);
        return m.find() ? m.group(group) : null;
    }

    private String extractSuningProductId(String url) {
        Matcher m = SUNING_PATTERN.matcher(url);
        if (m.find()) {
            // 苏宁使用 catalogCode_productCode 组合标识
            return m.group(1) + "_" + m.group(2);
        }
        return null;
    }

    // ================== 标准化URL构建 ==================

    private String buildNormalizedUrl(EcommercePlatform platform, URI uri,
                                      String productId, String originalUrl) {
        if (productId == null) return originalUrl;

        return switch (platform) {
            case TAOBAO     -> "https://item.taobao.com/item.htm?id=" + productId;
            case TMALL      -> "https://detail.tmall.com/item.htm?id=" + productId;
            case JD         -> "https://item.jd.com/" + productId + ".html";
            case PINDUODUO  -> "https://mobile.yangkeduo.com/goods.html?goods_id=" + productId;
            case SUNING     -> buildSuningUrl(productId);
            case AMAZON_CN  -> "https://www.amazon.cn/dp/" + productId + "/";
            case XIAOHONGSHU -> "https://www.xiaohongshu.com/explore/" + productId;
            default         -> stripTrackingParams(uri, originalUrl);
        };
    }

    private String buildSuningUrl(String productId) {
        String[] parts = productId.split("_");
        if (parts.length == 2) {
            return "https://product.suning.com/" + parts[0] + "/" + parts[1] + ".html";
        }
        return "https://www.suning.com";
    }

    /**
     * 去除URL中的追踪参数（通用降级处理）
     */
    private String stripTrackingParams(URI uri, String originalUrl) {
        try {
            String query = uri.getQuery();
            if (StringUtils.isBlank(query)) return originalUrl;

            Map<String, String> params = new HashMap<>();
            for (String pair : query.split("&")) {
                int idx = pair.indexOf('=');
                if (idx > 0) {
                    String key = URLDecoder.decode(pair.substring(0, idx), StandardCharsets.UTF_8);
                    String val = URLDecoder.decode(pair.substring(idx + 1), StandardCharsets.UTF_8);
                    params.put(key, val);
                }
            }
            // 删除追踪参数
            for (String tp : TRACKING_PARAMS) {
                params.remove(tp);
            }
            if (params.isEmpty()) {
                return uri.getScheme() + "://" + uri.getHost() + uri.getPath();
            }
            StringBuilder sb = new StringBuilder(uri.getScheme() + "://" + uri.getHost() + uri.getPath() + "?");
            params.forEach((k, v) -> sb.append(k).append("=").append(v).append("&"));
            sb.deleteCharAt(sb.length() - 1);
            return sb.toString();
        } catch (Exception e) {
            return originalUrl;
        }
    }

    // ================== 结果对象 ==================

    @lombok.Data
    @lombok.Builder
    public static class ParseResult {
        private EcommercePlatform platform;
        private String productId;
        private String normalizedUrl;
        private String originalUrl;
        private boolean success;
        private String failReason;

        public static ParseResult failed(String reason) {
            return ParseResult.builder()
                    .platform(EcommercePlatform.UNKNOWN)
                    .success(false)
                    .failReason(reason)
                    .build();
        }
    }
}
