package com.health.physical.core.controller;

import com.health.physical.common.entity.Resident;
import com.health.physical.common.exception.BusinessException;
import com.health.physical.core.service.ResidentService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * 居民管理接口单元测试（服务层已解耦，Mock ResidentService）
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("ResidentController - 居民管理接口测试")
class ResidentControllerTest {

    @Mock
    private ResidentService residentService;

    @InjectMocks
    private ResidentController controller;

    @Test
    @DisplayName("按身份证查询 - 存在时返回200")
    void getByIdCard_found() {
        Resident resident = new Resident();
        resident.setId(1L);
        resident.setIdCard("441322198505050505");
        resident.setName("张三");
        resident.setStatus(1);
        when(residentService.getByIdCard("441322198505050505")).thenReturn(resident);

        var result = controller.getByIdCard("441322198505050505");
        assertEquals(200, result.getCode());
        assertEquals("张三", result.getData().getName());
    }

    @Test
    @DisplayName("按身份证查询 - 不存在时返回404")
    void getByIdCard_notFound() {
        when(residentService.getByIdCard("000000000000000000")).thenReturn(null);

        var result = controller.getByIdCard("000000000000000000");
        assertEquals(404, result.getCode());
    }

    @Test
    @DisplayName("新增居民 - 身份证已存在时抛出BusinessException")
    void save_idCardExists_throwsException() {
        Resident newResident = new Resident();
        newResident.setIdCard("441322198505050505");
        newResident.setName("李四");
        when(residentService.save(newResident))
                .thenThrow(BusinessException.of("居民身份证已存在：441322198505050505"));

        assertThrows(BusinessException.class, () -> controller.save(newResident));
    }

    @Test
    @DisplayName("新增居民 - 正常新增返回200")
    void save_newResident_success() {
        Resident newResident = new Resident();
        newResident.setIdCard("441322199001010101");
        newResident.setName("王五");
        newResident.setStatus(1);
        when(residentService.save(newResident)).thenReturn(newResident);

        var result = controller.save(newResident);
        assertEquals(200, result.getCode());
        assertEquals("王五", result.getData().getName());
    }
}
