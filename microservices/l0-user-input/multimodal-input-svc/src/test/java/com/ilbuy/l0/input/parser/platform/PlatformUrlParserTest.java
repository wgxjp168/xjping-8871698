package com.ilbuy.l0.input.parser.platform;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 电商平台URL解析器单元测试
 *
 * <p>覆盖7大平台的URL解析正确性和边界场景。
 */
@DisplayName("PlatformUrlParser - 7大电商平台URL解析")
class PlatformUrlParserTest {

    private PlatformUrlParser parser;

    @BeforeEach
    void setUp() {
        parser = new PlatformUrlParser();
    }

    // ==================== 京东 ====================
    @Nested
    @DisplayName("京东链接解析")
    class JdTests {

        @Test
        @DisplayName("标准商品链接解析成功")
        void parseJdItemUrl() {
            String url = "https://item.jd.com/100012345678.html?utm_source=baidu&spm=xxx";
            PlatformUrlParser.ParseResult result = parser.parse(url);

            assertThat(result.isSuccess()).isTrue();
            assertThat(result.getPlatform()).isEqualTo(EcommercePlatform.JD);
            assertThat(result.getProductId()).isEqualTo("100012345678");
            assertThat(result.getNormalizedUrl()).isEqualTo("https://item.jd.com/100012345678.html");
        }

        @Test
        @DisplayName("移动端京东链接解析成功")
        void parseMobileJdUrl() {
            String url = "https://item.m.jd.com/product/100012345678.html";
            PlatformUrlParser.ParseResult result = parser.parse(url);

            assertThat(result.isSuccess()).isTrue();
            assertThat(result.getPlatform()).isEqualTo(EcommercePlatform.JD);
        }
    }

    // ==================== 淘宝 ====================
    @Nested
    @DisplayName("淘宝链接解析")
    class TaobaoTests {

        @Test
        @DisplayName("淘宝商品链接解析成功")
        void parseTaobaoUrl() {
            String url = "https://item.taobao.com/item.htm?id=123456789012&spm=xxx&pvid=yyy";
            PlatformUrlParser.ParseResult result = parser.parse(url);

            assertThat(result.isSuccess()).isTrue();
            assertThat(result.getPlatform()).isEqualTo(EcommercePlatform.TAOBAO);
            assertThat(result.getProductId()).isEqualTo("123456789012");
            assertThat(result.getNormalizedUrl())
                    .isEqualTo("https://item.taobao.com/item.htm?id=123456789012");
        }
    }

    // ==================== 天猫 ====================
    @Nested
    @DisplayName("天猫链接解析")
    class TmallTests {

        @Test
        @DisplayName("天猫详情链接解析成功")
        void parseTmallUrl() {
            String url = "https://detail.tmall.com/item.htm?id=987654321&ali_trackid=abc";
            PlatformUrlParser.ParseResult result = parser.parse(url);

            assertThat(result.isSuccess()).isTrue();
            assertThat(result.getPlatform()).isEqualTo(EcommercePlatform.TMALL);
            assertThat(result.getProductId()).isEqualTo("987654321");
        }
    }

    // ==================== 拼多多 ====================
    @Nested
    @DisplayName("拼多多链接解析")
    class PddTests {

        @Test
        @DisplayName("拼多多移动端链接解析成功")
        void parsePddMobileUrl() {
            String url = "https://mobile.yangkeduo.com/goods.html?goods_id=555666777&from=xxxxx";
            PlatformUrlParser.ParseResult result = parser.parse(url);

            assertThat(result.isSuccess()).isTrue();
            assertThat(result.getPlatform()).isEqualTo(EcommercePlatform.PINDUODUO);
            assertThat(result.getProductId()).isEqualTo("555666777");
            assertThat(result.getNormalizedUrl())
                    .isEqualTo("https://mobile.yangkeduo.com/goods.html?goods_id=555666777");
        }
    }

    // ==================== 苏宁 ====================
    @Nested
    @DisplayName("苏宁链接解析")
    class SuningTests {

        @Test
        @DisplayName("苏宁商品链接解析成功")
        void parseSuningUrl() {
            String url = "https://product.suning.com/0070179278/11258669671.html?safp=d488778a.phone";
            PlatformUrlParser.ParseResult result = parser.parse(url);

            assertThat(result.isSuccess()).isTrue();
            assertThat(result.getPlatform()).isEqualTo(EcommercePlatform.SUNING);
            assertThat(result.getProductId()).isEqualTo("0070179278_11258669671");
        }
    }

    // ==================== 亚马逊 ====================
    @Nested
    @DisplayName("亚马逊中国链接解析")
    class AmazonTests {

        @Test
        @DisplayName("亚马逊ASIN解析成功")
        void parseAmazonUrl() {
            String url = "https://www.amazon.cn/dp/B08N5WRWNW/ref=sr_1_1";
            PlatformUrlParser.ParseResult result = parser.parse(url);

            assertThat(result.isSuccess()).isTrue();
            assertThat(result.getPlatform()).isEqualTo(EcommercePlatform.AMAZON_CN);
            assertThat(result.getProductId()).isEqualTo("B08N5WRWNW");
            assertThat(result.getNormalizedUrl())
                    .isEqualTo("https://www.amazon.cn/dp/B08N5WRWNW/");
        }
    }

    // ==================== 小红书 ====================
    @Nested
    @DisplayName("小红书链接解析")
    class XhsTests {

        @Test
        @DisplayName("小红书商品笔记链接解析成功")
        void parseXhsUrl() {
            String url = "https://www.xiaohongshu.com/explore/64a1234abcd5678";
            PlatformUrlParser.ParseResult result = parser.parse(url);

            assertThat(result.isSuccess()).isTrue();
            assertThat(result.getPlatform()).isEqualTo(EcommercePlatform.XIAOHONGSHU);
            assertThat(result.getProductId()).isEqualTo("64a1234abcd5678");
        }
    }

    // ==================== 边界场景 ====================
    @Nested
    @DisplayName("边界场景")
    class EdgeCaseTests {

        @Test
        @DisplayName("空URL返回失败")
        void emptyUrlFails() {
            PlatformUrlParser.ParseResult result = parser.parse("");
            assertThat(result.isSuccess()).isFalse();
            assertThat(result.getPlatform()).isEqualTo(EcommercePlatform.UNKNOWN);
        }

        @Test
        @DisplayName("null URL返回失败")
        void nullUrlFails() {
            PlatformUrlParser.ParseResult result = parser.parse(null);
            assertThat(result.isSuccess()).isFalse();
        }

        @Test
        @DisplayName("非电商URL识别为UNKNOWN")
        void unknownPlatformUrl() {
            PlatformUrlParser.ParseResult result = parser.parse("https://www.baidu.com/s?wd=test");
            assertThat(result.isSuccess()).isFalse();
            assertThat(result.getPlatform()).isEqualTo(EcommercePlatform.UNKNOWN);
        }

        @Test
        @DisplayName("无协议头URL自动补全https")
        void urlWithoutProtocol() {
            PlatformUrlParser.ParseResult result = parser.parse("item.jd.com/100012345.html");
            assertThat(result.isSuccess()).isTrue();
            assertThat(result.getPlatform()).isEqualTo(EcommercePlatform.JD);
        }
    }

    // ==================== EcommercePlatform 枚举测试 ====================
    @ParameterizedTest
    @DisplayName("各平台域名识别正确")
    @CsvSource({
            "taobao.com,      TAOBAO",
            "tmall.com,       TMALL",
            "jd.com,          JD",
            "pinduoduo.com,   PINDUODUO",
            "suning.com,      SUNING",
            "amazon.cn,       AMAZON_CN",
            "xiaohongshu.com, XIAOHONGSHU"
    })
    void platformDetectionByHost(String host, String expectedPlatform) {
        EcommercePlatform platform = EcommercePlatform.fromHost(host);
        assertThat(platform.name()).isEqualTo(expectedPlatform);
    }
}
