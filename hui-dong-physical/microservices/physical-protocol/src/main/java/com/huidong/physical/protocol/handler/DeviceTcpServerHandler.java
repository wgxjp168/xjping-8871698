package com.huidong.physical.protocol.handler;

import com.huidong.physical.protocol.dto.HL7ParseResult;
import com.huidong.physical.protocol.parser.HL7MessageParser;
import com.huidong.physical.protocol.service.LabResultDispatcher;
import io.netty.channel.ChannelHandler;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.SimpleChannelInboundHandler;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 设备TCP接入处理器（Netty）
 * 接收院内设备（生化仪、血常规仪、糖化血红蛋白仪）上传的HL7报文
 */
@Slf4j
@Component
@ChannelHandler.Sharable
@RequiredArgsConstructor
public class DeviceTcpServerHandler extends SimpleChannelInboundHandler<String> {

    private final HL7MessageParser hl7Parser;
    private final LabResultDispatcher dispatcher;

    @Override
    protected void channelRead0(ChannelHandlerContext ctx, String msg) {
        String remoteAddr = ctx.channel().remoteAddress().toString();
        log.info("[TCP设备] 收到数据: from={}, length={}", remoteAddr, msg.length());

        try {
            // 解析HL7报文
            HL7ParseResult result = hl7Parser.parseOruR01(msg);
            // 分发检验结果到core服务（通过Kafka）
            dispatcher.dispatch(result);
            // 返回ACK确认
            ctx.writeAndFlush(buildAck(result));
        } catch (Exception e) {
            log.error("[TCP设备] 处理异常: from={}, error={}", remoteAddr, e.getMessage());
            ctx.writeAndFlush(buildNack(e.getMessage()));
        }
    }

    @Override
    public void channelActive(ChannelHandlerContext ctx) {
        log.info("[TCP设备] 设备连接: {}", ctx.channel().remoteAddress());
    }

    @Override
    public void channelInactive(ChannelHandlerContext ctx) {
        log.info("[TCP设备] 设备断开: {}", ctx.channel().remoteAddress());
    }

    @Override
    public void exceptionCaught(ChannelHandlerContext ctx, Throwable cause) {
        log.error("[TCP设备] 通道异常: {}", cause.getMessage());
        ctx.close();
    }

    private String buildAck(HL7ParseResult result) {
        // 标准HL7 ACK应答
        return "MSH|^~\\&|PHYSICAL_SYSTEM||" + result.getSendingApp()
                + "||" + result.getMessageDateTime()
                + "||ACK|" + System.currentTimeMillis() + "|P|2.5\r"
                + "MSA|AA|" + result.getMessageDateTime() + "|消息处理成功\r";
    }

    private String buildNack(String errorMsg) {
        return "MSH|^~\\&|PHYSICAL_SYSTEM|||"
                + "||ACK|" + System.currentTimeMillis() + "|P|2.5\r"
                + "MSA|AE||消息处理失败: " + errorMsg + "\r";
    }
}
