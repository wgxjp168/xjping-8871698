package com.hd.device.file;

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
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * 文件型LIS设备监控服务
 * 适配设备：
 *   迈瑞 BS330 (生化) — LIS文件输出
 *   万瑞 BS830 (生化) — LIS文件输出
 *
 * 工作方式：
 *   设备将检验结果写入共享目录（如 C:\LIS_Output\BS330\）
 *   本服务监控该目录，发现新文件后解析并入库
 *   支持 ASTM 格式文本文件(.lis/.txt/.dat)
 */
@Component
public class FileDeviceWatcher {

    private static final Logger log = LoggerFactory.getLogger(FileDeviceWatcher.class);

    @Value("${device.file.enabled:true}")
    private boolean fileEnabled;

    @Value("${device.file.charset:GBK}")
    private String fileCharset;

    @Autowired
    private DeviceInfoService deviceInfoService;

    @Autowired
    private DeviceDataService deviceDataService;

    private final ExecutorService executor = Executors.newCachedThreadPool();

    @EventListener(ApplicationReadyEvent.class)
    public void startFileWatchers() {
        if (!fileEnabled) {
            log.info("File device watcher disabled.");
            return;
        }
        List<DeviceInfo> devices = deviceInfoService.listAll();
        int started = 0;
        for (DeviceInfo device : devices) {
            if ("FILE".equalsIgnoreCase(device.getConnectMode())
                    && device.getIpAddress() != null
                    && !device.getIpAddress().isEmpty()) {
                executor.submit(() -> watchDirectory(device));
                started++;
            }
        }
        if (started > 0) {
            log.info("Started {} file device watcher(s)", started);
        }
    }

    /**
     * 监控单个设备的输出目录
     * FILE模式下 comm_host 存储监控目录路径（如 C:\LIS\BS330）
     */
    private void watchDirectory(DeviceInfo device) {
        String dirPath = device.getIpAddress();
        log.info("File watcher starting: device={}, dir={}", device.getDeviceName(), dirPath);

        Path dir = Paths.get(dirPath);
        // 若目录不存在则创建
        try {
            Files.createDirectories(dir);
        } catch (IOException e) {
            log.error("Cannot create/access directory {}: {}", dirPath, e.getMessage());
            return;
        }

        // 先处理已存在的文件（启动时补处理）
        processExistingFiles(dir, device);

        // 启动WatchService持续监控
        try (WatchService watchService = FileSystems.getDefault().newWatchService()) {
            dir.register(watchService,
                    StandardWatchEventKinds.ENTRY_CREATE,
                    StandardWatchEventKinds.ENTRY_MODIFY);
            log.info("Watching directory {} for device {}", dir, device.getDeviceName());

            while (!Thread.currentThread().isInterrupted()) {
                WatchKey key;
                try {
                    key = watchService.take();
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                }
                for (WatchEvent<?> event : key.pollEvents()) {
                    WatchEvent.Kind<?> kind = event.kind();
                    if (kind == StandardWatchEventKinds.OVERFLOW) continue;

                    @SuppressWarnings("unchecked")
                    Path fileName = ((WatchEvent<Path>) event).context();
                    Path fullPath = dir.resolve(fileName);

                    if (isLisFile(fileName.toString())) {
                        log.info("New LIS file detected: {}", fullPath);
                        // 等待文件写完
                        sleep(500);
                        processFile(fullPath, device);
                    }
                }
                if (!key.reset()) {
                    log.warn("WatchKey invalid for {}, stopping watcher", dirPath);
                    break;
                }
            }
        } catch (IOException e) {
            log.error("File watcher error for {}: {}", dirPath, e.getMessage());
        }
    }

    private void processExistingFiles(Path dir, DeviceInfo device) {
        try {
            Files.list(dir)
                    .filter(p -> isLisFile(p.getFileName().toString()))
                    .sorted()
                    .forEach(f -> processFile(f, device));
        } catch (IOException e) {
            log.error("Error listing existing files in {}: {}", dir, e.getMessage());
        }
    }

    private void processFile(Path file, DeviceInfo device) {
        try {
            Charset cs;
            try {
                cs = Charset.forName(fileCharset);
            } catch (Exception e) {
                cs = StandardCharsets.UTF_8;
            }
            String content = new String(Files.readAllBytes(file), cs);
            if (content.trim().isEmpty()) return;

            List<String> lines = AstmParser.extractRecordLines(content.getBytes(cs));
            if (lines.isEmpty()) {
                log.warn("No ASTM records in file {}", file);
                return;
            }
            AstmMessage message = AstmParser.parseMessage(lines);
            log.info("File ASTM message from {}: file={}, sampleId={}, results={}",
                    device.getDeviceName(), file.getFileName(), message.getSampleId(),
                    message.getResultRecords().size());
            deviceDataService.saveAstmMessage(message, content, "FILE:" + file.toAbsolutePath());

            // 处理完毕后重命名为 .done 防止重复处理
            Path donePath = file.resolveSibling(file.getFileName() + ".done");
            Files.move(file, donePath, StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException e) {
            log.error("Error reading file {}: {}", file, e.getMessage());
        } catch (Exception e) {
            log.error("Error processing file {}: {}", file, e.getMessage(), e);
        }
    }

    private boolean isLisFile(String name) {
        String lower = name.toLowerCase();
        return (lower.endsWith(".lis") || lower.endsWith(".txt") || lower.endsWith(".dat")
                || lower.endsWith(".astm") || lower.endsWith(".result"))
                && !lower.endsWith(".done");
    }

    private void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException ignored) { Thread.currentThread().interrupt(); }
    }
}
