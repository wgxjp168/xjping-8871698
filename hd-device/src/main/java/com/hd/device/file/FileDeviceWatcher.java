package com.hd.device.file;

import com.hd.device.entity.DeviceInfo;
import com.hd.device.service.DeviceInfoService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.event.ContextRefreshedEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class FileDeviceWatcher {

    private static final Logger log = LoggerFactory.getLogger(FileDeviceWatcher.class);

    @Autowired
    private DeviceInfoService deviceInfoService;

    @EventListener(ContextRefreshedEvent.class)
    public void startFileWatchers() {
        List<DeviceInfo> devices = deviceInfoService.listAll();
        log.info("Starting file watchers for {} devices", devices.size());

        for (DeviceInfo device : devices) {
            if ("FILE".equalsIgnoreCase(device.getConnectMode())) {
                startWatcherForDevice(device);
            }
        }
    }

    private void startWatcherForDevice(DeviceInfo device) {
        log.info("Starting file watcher for device: {} ({})", device.getDeviceName(), device.getDeviceNo());
        // File watcher implementation
    }
}
