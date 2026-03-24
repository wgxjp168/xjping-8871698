<template>
  <div class="lab-scan-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <el-icon color="#409EFF"><Barcode /></el-icon>
          <span>标本扫码核对</span>
          <el-tag type="info" size="small">扫码枪扫描标本条码</el-tag>
        </div>
      </template>

      <el-input
        ref="inputRef"
        v-model="barcode"
        placeholder="扫描标本条码（扫码枪自动触发）"
        size="large"
        clearable
        @keyup.enter="handleScan"
        class="scan-input"
      >
        <template #append>
          <el-button type="primary" :loading="loading" @click="handleScan">核对</el-button>
        </template>
      </el-input>

      <el-divider v-if="result" />

      <el-descriptions v-if="result" :column="3" border>
        <el-descriptions-item label="居民姓名"><strong>{{ result.name }}</strong></el-descriptions-item>
        <el-descriptions-item label="身份证">{{ result.idCard }}</el-descriptions-item>
        <el-descriptions-item label="体检批次">{{ result.batchNo }}</el-descriptions-item>
        <el-descriptions-item label="标本类型">{{ result.specimenType || '血液/尿液' }}</el-descriptions-item>
        <el-descriptions-item label="检验项目">
          <el-tag v-for="p in (result.projects || [])" :key="p" size="small" class="m-1">{{ p }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag type="success">已核对</el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'

const inputRef = ref(null)
const barcode = ref('')
const loading = ref(false)
const result = ref(null)

onMounted(() => nextTick(() => inputRef.value?.focus()))

async function handleScan() {
  if (!barcode.value.trim()) {
    ElMessage.warning('请扫描标本条码')
    return
  }
  loading.value = true
  try {
    // TODO: 调用后端接口 /api/core/specimens/scan
    // 模拟数据
    await new Promise(r => setTimeout(r, 300))
    result.value = {
      name: '张三',
      idCard: '44132219800101****',
      batchNo: 'HY20240324',
      projects: ['BIOCHEM', 'CBC', 'HBA1C']
    }
    ElMessage.success('标本核对成功')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="less">
.card-header {
  display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: 600;
}
.scan-input {
  :deep(.el-input__inner) { font-size: 18px; height: 48px; }
}
.m-1 { margin: 2px; }
</style>
