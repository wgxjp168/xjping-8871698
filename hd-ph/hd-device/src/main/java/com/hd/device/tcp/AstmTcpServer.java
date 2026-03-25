package com.hd.device.tcp;

import com.hd.device.protocol.AstmMessage;
import com.hd.device.protocol.AstmParser;
import com.hd.device.service.DeviceDataService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * ASTM TCP服务端
 * 监听端口7100，等待设备主动连接并上传检验数据
 * 支持所有 ASTM E1381/E1394 兼容设备
 */
@Component
public class AstmTcpServer {

    private static final Logger log = LoggerFactory.getLogger(AstmTcpServer.class);

    @Value("${device.tcp.port:7100}")
    private int tcpPort;

    @Value("${device.tcp.enabled:true}")
    private boolean enabled;

    @Autowired
    private DeviceDataService deviceDataService;

    private final ExecutorService executor = Executors.newCachedThreadPool();

    @EventListener(ApplicationReadyEvent.class)
    public void startServer() {
        if (!enabled) {
            log.info("ASTM TCP Server disabled.");
            return;
        }
        executor.submit(this::run);
    }

    private void run() {
        log.info("ASTM TCP Server starting on port {}", tcpPort);
        try (ServerSocket serverSocket = new ServerSocket(tcpPort)) {
            log.info("ASTM TCP Server listening on port {}", tcpPort);
            while (!Thread.currentThread().isInterrupted()) {
                try {
                    Socket client = serverSocket.accept();
                    log.info("Device connected from: {}", client.getRemoteSocketAddress());
                    executor.submit(() -> handleClient(client));
                } catch (IOException e) {
                    log.error("Accept error: {}", e.getMessage());
                }
            }
        } catch (IOException e) {
            log.error("TCP Server failed to start on port {}: {}", tcpPort, e.getMessage());
        }
    }

    private void handleClient(Socket socket) {
        String remoteAddr = socket.getRemoteSocketAddress().toString();
        log.info("Handling ASTM session from {}", remoteAddr);
        try (InputStream in = socket.getInputStream();
             OutputStream out = socket.getOutputStream()) {

            byte[] buffer = new byte[65536];
            StringBuilder messageBuffer = new StringBuilder();
            boolean sessionActive = true;

            while (sessionActive) {
                int bytesRead = in.read(buffer);
                if (bytesRead < 0) {
                    break;
                }
                byte[] data = new byte[bytesRead];
                System.arraycopy(buffer, 0, data, 0, bytesRead);

                // 检查是否是 ENQ（设备请求发送）
                if (bytesRead == 1 && data[0] == AstmParser.ENQ) {
                    log.debug("Received ENQ from {}", remoteAddr);
                    out.write(AstmParser.ACK);
                    out.flush();
                    continue;
                }

                // 检查是否是 EOT（传输结束）
                if (bytesRead == 1 && data[0] == AstmParser.EOT) {
                    log.info("Received EOT from {}, processing message", remoteAddr);
                    if (messageBuffer.length() > 0) {
                        processMessage(messageBuffer.toString().getBytes(), remoteAddr);
                        messageBuffer = new StringBuilder();
                    }
                    sessionActive = false;
                    continue;
                }

                // 累积数据帧
                messageBuffer.append(new String(data));

                // ACK每个完整帧（含ETX/ETB）
                for (byte b : data) {
                    if (b == AstmParser.ETX || b == AstmParser.ETB) {
                        out.write(AstmParser.ACK);
                        out.flush();
                        break;
                    }
                }
            }
        } catch (IOException e) {
            log.error("Error handling client {}: {}", remoteAddr, e.getMessage());
        } finally {
            try { socket.close(); } catch (IOException ignored) {}
            log.info("Device disconnected: {}", remoteAddr);
        }
    }

    private void processMessage(byte[] rawData, String remoteAddr) {
        try {
            List<String> lines = AstmParser.extractRecordLines(rawData);
            if (lines.isEmpty()) {
                log.warn("No parseable lines from {}", remoteAddr);
                return;
            }
            AstmMessage message = AstmParser.parseMessage(lines);
            log.info("Parsed ASTM message from {}, sampleId={}, results={}",
                    remoteAddr, message.getSampleId(), message.getResultRecords().size());
            deviceDataService.saveAstmMessage(message, new String(rawData), remoteAddr);
        } catch (Exception e) {
            log.error("Failed to process ASTM message from {}: {}", remoteAddr, e.getMessage(), e);
        }
    }
}
