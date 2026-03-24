package com.health.physical.core.controller;

import com.alibaba.fastjson2.JSON;
import com.health.physical.common.entity.Resident;
import com.health.physical.core.mapper.ResidentMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * 居民管理接口单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("ResidentController - 居民管理接口测试")
class ResidentControllerTest {

    @Mock private ResidentMapper residentMapper;
    @InjectMocks private ResidentController controller;

    @Test
    @DisplayName("按身份证查询 - 存在时返回200")
    void getByIdCard_found() {
        Resident resident = new Resident();
        resident.setId(1L);
        resident.setIdCard("441322198505050505");
        resident.setName("张三");
        resident.setGender(1);
        resident.setStatus(1);

        when(residentMapper.selectByIdCard("441322198505050505")).thenReturn(resident);

        var result = controller.getByIdCard("441322198505050505");
        assertEquals(200, result.getCode());
        assertEquals("张三", result.getData().getName());
    }

    @Test
    @DisplayName("按身份证查询 - 不存在时返回404")
    void getByIdCard_notFound() {
        when(residentMapper.selectByIdCard("000000000000000000")).thenReturn(null);

        var result = controller.getByIdCard("000000000000000000");
        assertEquals(404, result.getCode());
    }

    @Test
    @DisplayName("新增居民 - 身份证已存在时返回错误")
    void save_idCardExists_returnsFail() {
        Resident existing = new Resident();
        existing.setId(1L);
        existing.setIdCard("441322198505050505");

        Resident newResident = new Resident();
        newResident.setIdCard("441322198505050505");
        newResident.setName("李四");

        when(residentMapper.selectByIdCard("441322198505050505")).thenReturn(existing);

        var result = controller.save(newResident);
        assertNotEquals(200, result.getCode(), "已存在身份证不应允许重复新增");
    }

    @Test
    @DisplayName("新增居民 - 正常新增")
    void save_newResident_success() {
        Resident newResident = new Resident();
        newResident.setIdCard("441322199001010101");
        newResident.setName("王五");

        when(residentMapper.selectByIdCard("441322199001010101")).thenReturn(null);
        when(residentMapper.insert(any(Resident.class))).thenReturn(1);

        var result = controller.save(newResident);
        assertEquals(200, result.getCode());
        assertEquals(1, result.getData().getStatus(), "新增居民状态应为1");
    }
}
