package com.hd.device.controller;

import com.hd.device.service.DeviceInfoService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/devices")
public class DeviceController {

    @Autowired
    private DeviceInfoService deviceInfoService;

    @GetMapping("/count/online")
    public ResponseEntity<Map<String, Object>> countOnline() {
        long count = deviceInfoService.countOnline();
        Map<String, Object> result = new HashMap<>();
        result.put("code", 200);
        result.put("data", count);
        result.put("msg", "success");
        return ResponseEntity.ok(result);
    }
}
