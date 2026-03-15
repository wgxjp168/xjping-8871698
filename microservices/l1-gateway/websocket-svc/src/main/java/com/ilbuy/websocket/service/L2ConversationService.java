package com.ilbuy.websocket.service;

import java.util.function.Consumer;

/**
 * L2 对话管理服务接口（预留，当前为桩实现）
 *
 * <p>与 L2 conversation-svc 对接，支持：
 * <ul>
 *   <li>流式 AI 回复（SSE → WebSocket 转发）</li>
 *   <li>多模态输入处理（文本 / 语音 / 图片 / 链接）</li>
 *   <li>对话上下文管理</li>
 * </ul>
 *
 * <p>阶段3（L2）实现后，替换为实际 Feign Client 调用。
 */
public interface L2ConversationService {

    /**
     * 处理文本输入
     *
     * @param userId       用户ID
     * @param sessionId    业务会话ID
     * @param content      用户文本内容
     * @param chunkHandler 流式回复块回调
     * @param doneHandler  完成回调
     * @param errorHandler 错误回调
     */
    void processText(String userId, String sessionId, String content,
                     Consumer<String> chunkHandler,
                     Runnable doneHandler,
                     Consumer<String> errorHandler);

    /**
     * 处理语音输入（base64 编码）
     */
    void processVoice(String userId, String sessionId, String audioBase64, String mediaType,
                      Consumer<String> chunkHandler,
                      Runnable doneHandler,
                      Consumer<String> errorHandler);

    /**
     * 处理图片输入（base64 编码）
     */
    void processImage(String userId, String sessionId, String imageBase64, String mediaType,
                      Consumer<String> chunkHandler,
                      Runnable doneHandler,
                      Consumer<String> errorHandler);

    /**
     * 处理商品链接输入
     */
    void processLink(String userId, String sessionId, String url,
                     Consumer<String> chunkHandler,
                     Runnable doneHandler,
                     Consumer<String> errorHandler);
}
