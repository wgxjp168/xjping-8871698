package com.health.physical.urine.service;

import com.health.physical.urine.entity.UrineResult;
import com.health.physical.urine.mapper.UrineResultMapper;
import com.health.physical.urine.service.impl.UrineServiceImpl;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Arrays;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * 尿机服务单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("UrineService 单元测试")
class UrineServiceTest {

    @Mock
    private UrineResultMapper urineResultMapper;

    @InjectMocks
    private UrineServiceImpl urineService;

    @Test
    @DisplayName("上传新结果 - 成功入库")
    void upload_newResult_insertAndReturn() {
        UrineResult result = buildResult("BC001", 1L);
        when(urineResultMapper.selectOne(any())).thenReturn(null);
        when(urineResultMapper.insert(any())).thenReturn(1);

        UrineResult uploaded = urineService.upload(result);

        assertThat(uploaded.getBarcode()).isEqualTo("BC001");
        assertThat(uploaded.getSyncStatus()).isEqualTo(0);
        assertThat(uploaded.getStatus()).isEqualTo(1);
        verify(urineResultMapper, times(1)).insert(any());
    }

    @Test
    @DisplayName("上传重复条码 - 返回已存在记录，不重复插入")
    void upload_duplicate_returnsExisting() {
        UrineResult existing = buildResult("BC001", 1L);
        existing.setId(10L);
        when(urineResultMapper.selectOne(any())).thenReturn(existing);

        UrineResult uploaded = urineService.upload(buildResult("BC001", 1L));

        assertThat(uploaded.getId()).isEqualTo(10L);
        verify(urineResultMapper, never()).insert(any());
    }

    @Test
    @DisplayName("按体检单ID查询 - 返回列表")
    void getByPhysicalId_returnsList() {
        List<UrineResult> list = Arrays.asList(
                buildResult("BC001", 1L),
                buildResult("BC002", 1L)
        );
        when(urineResultMapper.selectList(any())).thenReturn(list);

        List<UrineResult> result = urineService.getByPhysicalId(1L);
        assertThat(result).hasSize(2);
    }

    @Test
    @DisplayName("按条码查询 - 存在时返回记录")
    void getByBarcode_exists_returnsRecord() {
        UrineResult expected = buildResult("BC001", 1L);
        when(urineResultMapper.selectOne(any())).thenReturn(expected);

        UrineResult result = urineService.getByBarcode("BC001");
        assertThat(result).isNotNull();
        assertThat(result.getBarcode()).isEqualTo("BC001");
    }

    @Test
    @DisplayName("按条码查询 - 不存在时返回null")
    void getByBarcode_notFound_returnsNull() {
        when(urineResultMapper.selectOne(any())).thenReturn(null);

        UrineResult result = urineService.getByBarcode("NOT_EXIST");
        assertThat(result).isNull();
    }

    private UrineResult buildResult(String barcode, Long physicalId) {
        UrineResult r = new UrineResult();
        r.setBarcode(barcode);
        r.setPhysicalId(physicalId);
        r.setResidentId(100L);
        r.setLeu("neg");
        r.setNit("neg");
        r.setPro("neg");
        r.setGlu("neg");
        r.setDeleted(0);
        return r;
    }
}
