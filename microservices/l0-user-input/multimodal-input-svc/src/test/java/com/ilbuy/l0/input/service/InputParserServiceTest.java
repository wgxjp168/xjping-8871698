package com.ilbuy.l0.input.service;

import com.ilbuy.l0.input.domain.dto.InputRequest;
import com.ilbuy.l0.input.domain.dto.ParsedInput;
import com.ilbuy.l0.input.domain.enums.InputType;
import com.ilbuy.l0.input.parser.*;
import com.ilbuy.l0.input.parser.platform.EcommercePlatform;
import com.ilbuy.l0.input.parser.platform.PlatformUrlParser;
import com.ilbuy.l0.input.service.impl.InputParserServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

/**
 * InputParserService 综合单元测试
 *
 * <p>验证四种输入类型的解析流程完整性，不依赖 Spring Context。
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("InputParserService - 多模态输入解析集成测试")
class InputParserServiceTest {

    @Mock private ImageRecognitionService imageRecognitionService;
    @Mock private VoiceToTextService      voiceToTextService;

    private InputParserService parserService;

    @BeforeEach
    void setUp() {
        // VoiceToTextService mock 需要返回 providerCode
        when(voiceToTextService.providerCode()).thenReturn("baidu");

        PlatformUrlParser platformUrlParser = new PlatformUrlParser();
        TextInputParser  textParser  = new TextInputParser();
        ImageInputParser imageParser = new ImageInputParser(imageRecognitionService);
        LinkInputParser  linkParser  = new LinkInputParser(platformUrlParser);
        // VoiceInputParser 使用 List<VoiceToTextService> 注入
        VoiceInputParser voiceParser = new VoiceInputParser(
                List.of(voiceToTextService), textParser, "baidu");

        List<InputParser> parsers = List.of(textParser, imageParser, linkParser, voiceParser);
        parserService = new InputParserServiceImpl(parsers, List.of(voiceToTextService), "baidu");
    }

    // ==================== 文本解析测试 ====================

    @Test
    @DisplayName("文本解析：提取关键词和预算上限")
    void parseTextWithBudgetMax() {
        InputRequest request = new InputRequest();
        request.setInputType(InputType.TEXT);
        request.setTextContent("我想买一台5000元以内的游戏本");
        request.setUserId(1L);

        ParsedInput result = parserService.parse(request);

        assertThat(result.isSuccess()).isTrue();
        assertThat(result.getProductKeyword()).contains("游戏本");
        assertThat(result.getBudgetMax()).isEqualByComparingTo(new BigDecimal("5000"));
        assertThat(result.getBudgetMin()).isNull();
        assertThat(result.getInputType()).isEqualTo(InputType.TEXT);
    }

    @Test
    @DisplayName("文本解析：提取预算区间")
    void parseTextWithBudgetRange() {
        InputRequest request = new InputRequest();
        request.setInputType(InputType.TEXT);
        request.setTextContent("帮我看看3000-5000元的无线蓝牙耳机");
        request.setUserId(1L);

        ParsedInput result = parserService.parse(request);

        assertThat(result.isSuccess()).isTrue();
        assertThat(result.getBudgetMin()).isEqualByComparingTo(new BigDecimal("3000"));
        assertThat(result.getBudgetMax()).isEqualByComparingTo(new BigDecimal("5000"));
        assertThat(result.getProductKeyword()).contains("蓝牙耳机");
    }

    @Test
    @DisplayName("文本解析：万元预算识别")
    void parseTextWithWanBudget() {
        InputRequest request = new InputRequest();
        request.setInputType(InputType.TEXT);
        request.setTextContent("1.5万以内的单反相机");
        request.setUserId(1L);

        ParsedInput result = parserService.parse(request);

        assertThat(result.isSuccess()).isTrue();
        assertThat(result.getBudgetMax()).isEqualByComparingTo(new BigDecimal("15000"));
    }

    // ==================== 链接解析测试 ====================

    @Test
    @DisplayName("链接解析：京东标准链接")
    void parseLinkJD() {
        InputRequest request = new InputRequest();
        request.setInputType(InputType.LINK);
        request.setRawUrl("https://item.jd.com/100023456789.html?spm=xxx");
        request.setUserId(1L);

        ParsedInput result = parserService.parse(request);

        assertThat(result.isSuccess()).isTrue();
        assertThat(result.getPlatform()).isEqualTo(EcommercePlatform.JD);
        assertThat(result.getPlatformProductId()).isEqualTo("100023456789");
        assertThat(result.getNormalizedUrl()).isEqualTo("https://item.jd.com/100023456789.html");
    }

    @Test
    @DisplayName("链接解析：亚马逊ASIN链接")
    void parseLinkAmazon() {
        InputRequest request = new InputRequest();
        request.setInputType(InputType.LINK);
        request.setRawUrl("https://www.amazon.cn/dp/B08N5WRWNW/ref=sr_1_1");
        request.setUserId(1L);

        ParsedInput result = parserService.parse(request);

        assertThat(result.isSuccess()).isTrue();
        assertThat(result.getPlatform()).isEqualTo(EcommercePlatform.AMAZON_CN);
        assertThat(result.getPlatformProductId()).isEqualTo("B08N5WRWNW");
    }

    @Test
    @DisplayName("链接解析：淘宝商品链接（含追踪参数）")
    void parseLinkTaobao() {
        InputRequest request = new InputRequest();
        request.setInputType(InputType.LINK);
        request.setRawUrl("https://item.taobao.com/item.htm?id=123456789012&spm=aaa&ali_trackid=xxx");
        request.setUserId(1L);

        ParsedInput result = parserService.parse(request);

        assertThat(result.isSuccess()).isTrue();
        assertThat(result.getPlatform()).isEqualTo(EcommercePlatform.TAOBAO);
        assertThat(result.getPlatformProductId()).isEqualTo("123456789012");
        // 标准化URL应去除追踪参数
        assertThat(result.getNormalizedUrl())
                .isEqualTo("https://item.taobao.com/item.htm?id=123456789012");
    }

    @Test
    @DisplayName("链接解析：拼多多商品链接")
    void parseLinkPDD() {
        InputRequest request = new InputRequest();
        request.setInputType(InputType.LINK);
        request.setRawUrl("https://mobile.yangkeduo.com/goods.html?goods_id=555666777&from=xxx");
        request.setUserId(1L);

        ParsedInput result = parserService.parse(request);

        assertThat(result.isSuccess()).isTrue();
        assertThat(result.getPlatform()).isEqualTo(EcommercePlatform.PINDUODUO);
        assertThat(result.getPlatformProductId()).isEqualTo("555666777");
    }

    @Test
    @DisplayName("链接解析：非电商链接返回失败")
    void parseUnknownLink() {
        InputRequest request = new InputRequest();
        request.setInputType(InputType.LINK);
        request.setRawUrl("https://www.baidu.com/s?wd=游戏本");
        request.setUserId(1L);

        ParsedInput result = parserService.parse(request);

        assertThat(result.isSuccess()).isFalse();
        assertThat(result.getPlatform()).isEqualTo(EcommercePlatform.UNKNOWN);
    }

    // ==================== 图片解析测试 ====================

    @Test
    @DisplayName("图片解析：识别成功返回标签")
    void parseImageSuccess() {
        String imageUrl = "https://oss.ilbuy.com/input/image/laptop.jpg";
        when(imageRecognitionService.recognize(imageUrl))
                .thenReturn(ImageRecognitionService.RecognitionResult.ok(
                        List.of("笔记本电脑", "游戏本", "电子设备"),
                        List.of(0.95, 0.87, 0.76)
                ));

        InputRequest request = new InputRequest();
        request.setInputType(InputType.IMAGE);
        request.setFileUrl(imageUrl);
        request.setUserId(1L);

        ParsedInput result = parserService.parse(request);

        assertThat(result.isSuccess()).isTrue();
        assertThat(result.getProductKeyword()).isEqualTo("笔记本电脑");
        assertThat(result.getDetectedLabels()).containsExactly("笔记本电脑", "游戏本", "电子设备");
        assertThat(result.getImageUrl()).isEqualTo(imageUrl);
    }

    @Test
    @DisplayName("图片解析：识别失败返回失败结果")
    void parseImageFailure() {
        String imageUrl = "https://oss.ilbuy.com/input/image/bad.jpg";
        when(imageRecognitionService.recognize(imageUrl))
                .thenReturn(ImageRecognitionService.RecognitionResult.fail("图片质量过低"));

        InputRequest request = new InputRequest();
        request.setInputType(InputType.IMAGE);
        request.setFileUrl(imageUrl);
        request.setUserId(1L);

        ParsedInput result = parserService.parse(request);

        assertThat(result.isSuccess()).isFalse();
        assertThat(result.getFailReason()).contains("图片质量过低");
    }

    // ==================== 语音解析测试 ====================

    @Test
    @DisplayName("语音解析：转写成功后继续文本解析")
    void parseVoiceSuccess() {
        String audioUrl = "https://oss.ilbuy.com/input/audio/test.mp3";
        when(voiceToTextService.transcribe(anyString(), anyString()))
                .thenReturn(VoiceToTextService.TranscribeResult.ok("我想买2000元以内的运动鞋", 1200));

        InputRequest request = new InputRequest();
        request.setInputType(InputType.VOICE);
        request.setFileUrl(audioUrl);
        request.setVoiceProvider("baidu");
        request.setUserId(1L);

        ParsedInput result = parserService.parse(request);

        assertThat(result.isSuccess()).isTrue();
        assertThat(result.getInputType()).isEqualTo(InputType.VOICE);
        assertThat(result.getTranscribedText()).isEqualTo("我想买2000元以内的运动鞋");
        assertThat(result.getProductKeyword()).contains("运动鞋");
        assertThat(result.getBudgetMax()).isEqualByComparingTo(new BigDecimal("2000"));
    }

    @Test
    @DisplayName("语音解析：转写失败返回失败结果")
    void parseVoiceFailure() {
        String audioUrl = "https://oss.ilbuy.com/input/audio/noise.mp3";
        when(voiceToTextService.transcribe(anyString(), anyString()))
                .thenReturn(VoiceToTextService.TranscribeResult.fail("音频质量过低"));

        InputRequest request = new InputRequest();
        request.setInputType(InputType.VOICE);
        request.setFileUrl(audioUrl);
        request.setVoiceProvider("baidu");
        request.setUserId(1L);

        ParsedInput result = parserService.parse(request);

        assertThat(result.isSuccess()).isFalse();
        assertThat(result.getFailReason()).contains("音频质量过低");
    }

    // ==================== 批量解析测试 ====================

    @Test
    @DisplayName("批量解析：混合类型请求全部处理")
    void parseBatch() {
        InputRequest r1 = new InputRequest();
        r1.setInputType(InputType.TEXT);
        r1.setTextContent("买个机械键盘");
        r1.setUserId(1L);

        InputRequest r2 = new InputRequest();
        r2.setInputType(InputType.LINK);
        r2.setRawUrl("https://item.taobao.com/item.htm?id=987654321");
        r2.setUserId(1L);

        List<ParsedInput> results = parserService.parseBatch(List.of(r1, r2));

        assertThat(results).hasSize(2);
        assertThat(results.get(0).isSuccess()).isTrue();
        assertThat(results.get(1).isSuccess()).isTrue();
        assertThat(results.get(1).getPlatform()).isEqualTo(EcommercePlatform.TAOBAO);
    }
}
