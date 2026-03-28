package com.hd.device.serial;

import com.fazecast.jSerialComm.SerialPort;
import com.hd.device.entity.DeviceInfo;
import com.hd.device.protocol.AstmMessage;
import com.hd.device.protocol.AstmParser;
import com.hd.device.service.DeviceDataService;
import com.hd.device.service.DeviceInfoService;
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
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * 串口设备通信服务（RS232/USB转串口）
 * 适配设备：
 *   优利特 URIT-330 / URIT-560 (尿常规) — COM串口
 *   优利特 BH-5380CRP (血常规) — COM串口
 *   雷诺华 LD-600 (糖化血红蛋白) — COM串口
 *   理邦 DS-580i (血常规) — COM串口
 *
 * 协议：ASTM E1381 握手 + ASTM E1394 数据格式
 *   ENQ → ACK → 数据帧(STX/ETX) → ACK → EOT
 */
@Component
public class SerialDeviceServer {

    private static final Logger log = LoggerFactory.getLogger(SerialDeviceServer.class);

    @Value("${device.serial.enabled:true}")
    private boolean serialEnabled;

    @Autowired
    private DeviceInfoService deviceInfoService;

    @Autowired
    private DeviceDataService deviceDataService;

    private final ExecutorService executor = Executors.newCachedThreadPool();

    @EventListener(ApplicationReadyEvent.class)
    public void startSerialListeners() {
        if (!serialEnabled) {
            log.info("Serial device server disabled.");
            return;
        }
        List<DeviceInfo> devices = deviceInfoService.listAll();
        int started = 0;
        for (DeviceInfo device : devices) {
            if ("SERIAL".equalsIgnoreCase(device.getConnectMode())
                    && device.getIpAddress() != null
                    && !device.getIpAddress().isEmpty()) {
                executor.submit(() -> runSerialListener(device));
                started++;
            }
        }
        if (started > 0) {
            log.info("Started {} serial device listener(s)", started);
        }
    }

    /**
     * 持续监听单个串口设备，断开后自动重连
     */
    private void runSerialListener(DeviceInfo device) {
        String portName = device.getIpAddress(); // SERIAL模式下comm_host存储COM口名
        int baudRate = device.getBaudRate() != null ? device.getBaudRate() : 9600;
        log.info("Serial listener starting: device={}, port={}, baud={}", device.getDeviceName(), portName, baudRate);

        while (!Thread.currentThread().isInterrupted()) {
            SerialPort comPort = SerialPort.getCommPort(portName);
            comPort.setComPortParameters(baudRate, 8, SerialPort.ONE_STOP_BIT, SerialPort.NO_PARITY);
            comPort.setComPortTimeouts(SerialPort.TIMEOUT_READ_BLOCKING, 5000, 0);

            if (!comPort.openPort()) {
                log.warn("Cannot open serial port {}, retrying in 10s...", portName);
                sleep(10000);
                continue;
            }
            log.info("Serial port {} opened for device {}", portName, device.getDeviceName());

            try (InputStream in = comPort.getInputStream();
                 OutputStream out = comPort.getOutputStream()) {
                handleSerialSession(in, out, device);
            } catch (Exception e) {
                log.error("Serial error on {}: {}", portName, e.getMessage());
            } finally {
                comPort.closePort();
            }
            log.info("Serial port {} closed, reconnecting in 5s...", portName);
            sleep(5000);
        }
    }

    /**
     * 处理一次完整的串口通信会话（可接收多条ASTM消息）
     */
    private void handleSerialSession(InputStream in, OutputStream out, DeviceInfo device) throws IOException {
        byte[] buffer = new byte[65536];
        StringBuilder msgBuffer = new StringBuilder();

        while (!Thread.currentThread().isInterrupted()) {
            int n = in.read(buffer);
            if (n < 0) break;

            byte[] data = new byte[n];
            System.arraycopy(buffer, 0, data, 0, n);

            // ENQ: 设备请求发送
            if (n == 1 && data[0] == AstmParser.ENQ) {
                out.write(AstmParser.ACK);
                out.flush();
                log.debug("Serial ENQ received from {}, sent ACK", device.getDeviceName());
                continue;
            }

            // EOT: 一条消息传输结束
            if (n == 1 && data[0] == AstmParser.EOT) {
                if (msgBuffer.length() > 0) {
                    processSerialMessage(msgBuffer.toString().getBytes(), device);
                    msgBuffer = new StringBuilder();
                }
                continue;
            }

            // 累积帧数据
            msgBuffer.append(new String(data));

            // 每个完整帧末尾回ACK
            for (byte b : data) {
                if (b == AstmParser.ETX || b == AstmParser.ETB) {
                    out.write(AstmParser.ACK);
                    out.flush();
                    break;
                }
            }
        }
    }

    private void processSerialMessage(byte[] rawData, DeviceInfo device) {
        try {
            List<String> lines = AstmParser.extractRecordLines(rawData);
            if (lines.isEmpty()) {
                log.warn("No ASTM records from serial device {}", device.getDeviceName());
                return;
            }
            AstmMessage message = AstmParser.parseMessage(lines);
            log.info("Serial ASTM message from {}: sampleId={}, results={}",
                    device.getDeviceName(), message.getSampleId(), message.getResultRecords().size());
            deviceDataService.saveAstmMessage(message, new String(rawData), "SERIAL:" + device.getIpAddress());
        } catch (Exception e) {
            log.error("Failed to process serial message from {}: {}", device.getDeviceName(), e.getMessage(), e);
        }
    }

    private void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException ignored) { Thread.currentThread().interrupt(); }
    }
}
