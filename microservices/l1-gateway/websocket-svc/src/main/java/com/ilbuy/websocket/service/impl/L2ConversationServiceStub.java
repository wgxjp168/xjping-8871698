package com.ilbuy.websocket.service.impl;

import com.ilbuy.websocket.service.L2ConversationService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Primary;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.util.function.Consumer;

/**
 * L2 对话服务桩实现（阶段3 L2开发完成前使用）
 *
 * <p>模拟流式 AI 回复行为，便于前后端联调测试。
 * 阶段3完成后，通过配置切换为实际 Feign 调用。
 *
 * @author ILbuy Team
 */
@Slf4j
@Primary
@Service
public class L2ConversationServiceStub implements L2ConversationService {

    @Override
    @Async
    public void processText(String userId, String sessionId, String content,
                            Consumer<String> chunkHandler,
                            Runnable doneHandler,
                            Consumer<String> errorHandler) {
        log.info("[L2-STUB] 处理文本输入 userId={} sessionId={} content={}",
            userId, sessionId, content);
        try {
            // 模拟流式响应（实际由 L2 conversation-svc 提供）
            String[] parts = ("【AI决策建议-桩实现】\n" +
                "收到您的需求：\"" + content + "\"\n" +
                "正在分析最优采购方案...\n" +
                "当前为 L1 WebSocket 服务桩实现，L2 AI 决策服务（conversation-svc）开发完成后将提供真实分析。")
                .split("\n");

            for (String part : parts) {
                Thread.sleep(100);
                chunkHandler.accept(part + "\n");
            }
            doneHandler.run();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            errorHandler.accept("处理被中断");
        } catch (Exception e) {
            log.error("[L2-STUB] 处理失败: {}", e.getMessage());
            errorHandler.accept("AI 服务暂时不可用，请稍后重试");
        }
    }

    @Override
    @Async
    public void processVoice(String userId, String sessionId, String audioBase64, String mediaType,
                             Consumer<String> chunkHandler,
                             Runnable doneHandler,
                             Consumer<String> errorHandler) {
        log.info("[L2-STUB] 处理语音输入 userId={} sessionId={} mediaType={}", userId, sessionId, mediaType);
        try {
            Thread.sleep(200);
            chunkHandler.accept("【语音识别结果-桩实现】语音输入已接收，L2 语音处理服务开发完成后自动生效。\n");
            doneHandler.run();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            errorHandler.accept("处理被中断");
        }
    }

    @Override
    @Async
    public void processImage(String userId, String sessionId, String imageBase64, String mediaType,
                             Consumer<String> chunkHandler,
                             Runnable doneHandler,
                             Consumer<String> errorHandler) {
        log.info("[L2-STUB] 处理图片输入 userId={} sessionId={}", userId, sessionId);
        try {
            Thread.sleep(200);
            chunkHandler.accept("【图片识别结果-桩实现】图片输入已接收，L2 图像处理服务开发完成后自动生效。\n");
            doneHandler.run();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            errorHandler.accept("处理被中断");
        }
    }

    @Override
    @Async
    public void processLink(String userId, String sessionId, String url,
                            Consumer<String> chunkHandler,
                            Runnable doneHandler,
                            Consumer<String> errorHandler) {
        log.info("[L2-STUB] 处理链接输入 userId={} sessionId={} url={}", userId, sessionId, url);
        try {
            Thread.sleep(200);
            chunkHandler.accept("【链接解析结果-桩实现】链接已接收：" + url + "\nL2 链接解析服务开发完成后将提供完整商品分析。\n");
            doneHandler.run();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            errorHandler.accept("处理被中断");
        }
    }
}
