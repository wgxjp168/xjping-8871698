package com.health.physical.dr.service;

import com.health.physical.common.dto.PageResult;
import com.health.physical.common.exception.BusinessException;
import com.health.physical.dr.dto.DrScanRequest;
import com.health.physical.dr.dto.DrScanResponse;
import com.health.physical.dr.dto.DrSubmitRequest;
import com.health.physical.dr.entity.DrRecord;
import com.health.physical.dr.mapper.DrRecordMapper;
import com.health.physical.dr.service.impl.DrServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.redisson.api.RBucket;
import org.redisson.api.RedissonClient;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.Collections;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * DR服务单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("DrService - DR检查服务测试")
class DrServiceTest {

    @Mock private DrRecordMapper drRecordMapper;
    @Mock private RedissonClient redissonClient;
    @Mock private RestTemplate restTemplate;
    @Mock private RBucket<String> rBucket;

    @InjectMocks
    private DrServiceImpl drService;

    private DrRecord pendingRecord;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(drService, "authServiceUrl", "http://localhost:9005");
        ReflectionTestUtils.setField(drService, "countyApiUrl", "http://localhost:8080");
        ReflectionTestUtils.setField(drService, "countyApiToken", "");

        pendingRecord = new DrRecord();
        pendingRecord.setId(1L);
        pendingRecord.setDrCode("DR2024032400001");
        pendingRecord.setResidentId(100L);
        pendingRecord.setResidentName("李四");
        pendingRecord.setIdCard("441322198505050505");
        pendingRecord.setApplyNo("APPLY-001");
        pendingRecord.setExamPart("胸部正位");
        pendingRecord.setStatus(0); // 待检查
    }

    @Test
    @DisplayName("扫码成功 - 待检查状态，返回居民信息，canExam=1")
    void scanDrBarcode_pendingStatus_success() {
        DrScanRequest request = new DrScanRequest();
        request.setDrCode("DR2024032400001");

        when(drRecordMapper.selectByDrCode("DR2024032400001")).thenReturn(pendingRecord);
        when(drRecordMapper.update(any(), any())).thenReturn(1);
        when(redissonClient.getBucket(anyString())).thenReturn(rBucket);
        doNothing().when(rBucket).set(anyString(), anyLong(), any(TimeUnit.class));

        DrScanResponse response = drService.scanDrBarcode(request, "DOC001");

        assertNotNull(response);
        assertEquals(1, response.getCanExam(), "待检查状态应允许检查");
        assertEquals("李四", response.getResidentName());
        assertEquals("DR2024032400001", response.getDrCode());
        assertEquals("胸部正位", response.getExamPart());
        // 验证身份证已脱敏
        assertTrue(response.getIdCard().contains("*"), "身份证应脱敏");
        verify(drRecordMapper).update(any(), any()); // 验证状态已更新
    }

    @Test
    @DisplayName("扫码 - DR条码不存在，抛出BusinessException")
    void scanDrBarcode_notFound_throwsException() {
        DrScanRequest request = new DrScanRequest();
        request.setDrCode("DR_NOT_EXIST");

        when(drRecordMapper.selectByDrCode("DR_NOT_EXIST")).thenReturn(null);

        BusinessException ex = assertThrows(BusinessException.class,
                () -> drService.scanDrBarcode(request, "DOC001"));
        assertTrue(ex.getMessage().contains("DR条码不存在"), "异常消息应提示条码不存在");
    }

    @Test
    @DisplayName("扫码 - 已完成状态，canExam=0")
    void scanDrBarcode_completedStatus_cannotExam() {
        pendingRecord.setStatus(2); // 已完成
        DrScanRequest request = new DrScanRequest();
        request.setDrCode("DR2024032400001");

        when(drRecordMapper.selectByDrCode("DR2024032400001")).thenReturn(pendingRecord);

        DrScanResponse response = drService.scanDrBarcode(request, "DOC001");

        assertEquals(0, response.getCanExam(), "已完成状态不可重复检查");
        assertNotNull(response.getCannotReason(), "应有不可检查原因");
    }

    @Test
    @DisplayName("提交DR结果成功 - 状态更新为已完成")
    void submitDrResult_success() {
        pendingRecord.setStatus(1); // 检查中
        DrSubmitRequest request = new DrSubmitRequest();
        request.setId(1L);
        request.setDrCode("DR2024032400001");
        request.setDrResult("两肺纹理清晰，未见明显实质性病变，心影形态大小正常");
        request.setConclusion("NORMAL");
        request.setExamDoctorId("DOC001");
        request.setExamDoctor("张三");

        when(drRecordMapper.selectById(1L)).thenReturn(pendingRecord);
        when(drRecordMapper.update(any(), any())).thenReturn(1);
        // 模拟同步县域（异步，不关心结果）

        assertDoesNotThrow(() -> drService.submitDrResult(request, "DOC001"));
        verify(drRecordMapper).update(any(), any());
    }

    @Test
    @DisplayName("提交DR结果失败 - 记录不存在")
    void submitDrResult_notFound_throwsException() {
        DrSubmitRequest request = new DrSubmitRequest();
        request.setId(999L);
        request.setDrCode("DR_NOT_EXIST");
        request.setDrResult("正常");
        request.setConclusion("NORMAL");
        request.setExamDoctorId("DOC001");

        when(drRecordMapper.selectById(999L)).thenReturn(null);

        BusinessException ex = assertThrows(BusinessException.class,
                () -> drService.submitDrResult(request, "DOC001"));
        assertEquals("DR记录不存在", ex.getMessage());
    }

    @Test
    @DisplayName("提交DR结果失败 - 已完成状态不可重复提交")
    void submitDrResult_alreadyCompleted_throwsException() {
        pendingRecord.setStatus(2); // 已完成
        DrSubmitRequest request = new DrSubmitRequest();
        request.setId(1L);
        request.setDrCode("DR2024032400001");
        request.setDrResult("正常");
        request.setConclusion("NORMAL");
        request.setExamDoctorId("DOC001");

        when(drRecordMapper.selectById(1L)).thenReturn(pendingRecord);

        BusinessException ex = assertThrows(BusinessException.class,
                () -> drService.submitDrResult(request, "DOC001"));
        assertTrue(ex.getMessage().contains("已完成"), "异常消息应提示已完成");
    }

    @Test
    @DisplayName("注册DR开单 - 新条码正常入库")
    void registerDrOrder_newCode_success() {
        DrRecord order = new DrRecord();
        order.setDrCode("DR2024032400002");
        order.setResidentId(101L);
        order.setResidentName("王五");
        order.setExamPart("胸部正位");

        when(drRecordMapper.selectByDrCode("DR2024032400002")).thenReturn(null);
        when(drRecordMapper.insert(any(DrRecord.class))).thenReturn(1);

        DrRecord result = drService.registerDrOrder(order);

        assertNotNull(result);
        assertEquals(0, result.getStatus(), "注册后状态应为0-待检查");
        verify(drRecordMapper).insert(any(DrRecord.class));
    }

    @Test
    @DisplayName("注册DR开单 - 重复条码跳过插入")
    void registerDrOrder_duplicateCode_skipsInsert() {
        DrRecord existing = new DrRecord();
        existing.setId(99L);
        existing.setDrCode("DR_DUPLICATE");

        DrRecord order = new DrRecord();
        order.setDrCode("DR_DUPLICATE");

        when(drRecordMapper.selectByDrCode("DR_DUPLICATE")).thenReturn(existing);

        DrRecord result = drService.registerDrOrder(order);

        assertEquals(99L, result.getId(), "应返回已存在记录");
        verify(drRecordMapper, never()).insert(any()); // 不应触发insert
    }

    @Test
    @DisplayName("批量同步县域 - 空列表不报错")
    void batchSyncToCounty_emptyList_noException() {
        when(drRecordMapper.selectPendingSync(anyInt())).thenReturn(Collections.emptyList());
        assertDoesNotThrow(() -> drService.batchSyncToCounty());
    }
}
