package com.huidong.physical.protocol.config;

import com.huidong.physical.protocol.handler.DeviceTcpServerHandler;
import io.netty.bootstrap.ServerBootstrap;
import io.netty.channel.*;
import io.netty.channel.nio.NioEventLoopGroup;
import io.netty.channel.socket.SocketChannel;
import io.netty.channel.socket.nio.NioServerSocketChannel;
import io.netty.handler.codec.DelimiterBasedFrameDecoder;
import io.netty.handler.codec.Delimiters;
import io.netty.handler.codec.string.StringDecoder;
import io.netty.handler.codec.string.StringEncoder;
import io.netty.handler.timeout.IdleStateHandler;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;

/**
 * Netty TCP服务端配置
 * 用于接收院内检验设备（生化仪、血常规、糖化血红蛋白）上传的HL7报文
 */
@Slf4j
@Configuration
@RequiredArgsConstructor
public class NettyTcpServerConfig {

    @Value("${device.tcp.port:9999}")
    private int tcpPort;

    @Value("${device.tcp.boss-threads:1}")
    private int bossThreads;

    @Value("${device.tcp.worker-threads:4}")
    private int workerThreads;

    private final DeviceTcpServerHandler deviceHandler;

    private EventLoopGroup bossGroup;
    private EventLoopGroup workerGroup;
    private Channel serverChannel;

    @PostConstruct
    public void startServer() throws InterruptedException {
        bossGroup = new NioEventLoopGroup(bossThreads);
        workerGroup = new NioEventLoopGroup(workerThreads);

        ServerBootstrap bootstrap = new ServerBootstrap();
        bootstrap.group(bossGroup, workerGroup)
                .channel(NioServerSocketChannel.class)
                .option(ChannelOption.SO_BACKLOG, 128)
                .childOption(ChannelOption.SO_KEEPALIVE, true)
                .childOption(ChannelOption.TCP_NODELAY, true)
                .childHandler(new ChannelInitializer<SocketChannel>() {
                    @Override
                    protected void initChannel(SocketChannel ch) {
                        ChannelPipeline pipeline = ch.pipeline();
                        // 空闲检测（设备超过60s无数据则断开）
                        pipeline.addLast(new IdleStateHandler(60, 0, 0, TimeUnit.SECONDS));
                        // HL7报文以 \r 结束（EB + 0D + 1C 为MLLP协议）
                        pipeline.addLast(new DelimiterBasedFrameDecoder(65536, Delimiters.lineDelimiter()));
                        pipeline.addLast(new StringDecoder(StandardCharsets.UTF_8));
                        pipeline.addLast(new StringEncoder(StandardCharsets.UTF_8));
                        pipeline.addLast(deviceHandler);
                    }
                });

        ChannelFuture future = bootstrap.bind(tcpPort).sync();
        serverChannel = future.channel();
        log.info("设备TCP服务端启动成功，监听端口: {}", tcpPort);
    }

    @PreDestroy
    public void stopServer() {
        if (serverChannel != null) {
            serverChannel.close();
        }
        if (bossGroup != null) {
            bossGroup.shutdownGracefully();
        }
        if (workerGroup != null) {
            workerGroup.shutdownGracefully();
        }
        log.info("设备TCP服务端已停止");
    }
}
