<template>
  <div class="lab-results-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <el-icon color="#67C23A"><EditPen /></el-icon>
          <span>检验结果录入</span>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="生化检验 (BIOCHEM)" name="BIOCHEM">
          <p class="tab-tip">迈瑞生化仪自动上传结果，可在此查看和审核</p>
        </el-tab-pane>
        <el-tab-pane label="血常规 (CBC)" name="CBC">
          <p class="tab-tip">万瑞血常规仪自动上传结果</p>
        </el-tab-pane>
        <el-tab-pane label="糖化血红蛋白 (HBA1C)" name="HBA1C">
          <p class="tab-tip">万瑞糖化仪自动上传结果</p>
        </el-tab-pane>
        <el-tab-pane label="尿常规 (URINE)" name="URINE">
          <p class="tab-tip">优利特尿机（下乡4G上传 + 院内直连）</p>
        </el-tab-pane>
      </el-tabs>

      <el-table :data="tableData" stripe border v-loading="loading">
        <el-table-column prop="residentName" label="居民姓名" width="100" />
        <el-table-column prop="itemName" label="检验指标" width="140" />
        <el-table-column prop="resultValue" label="结果值" width="100" />
        <el-table-column prop="unit" label="单位" width="80" />
        <el-table-column prop="abnormalFlag" label="异常标志" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.abnormalFlag !== 'N'" :type="row.abnormalFlag === 'H' || row.abnormalFlag === 'L' ? 'warning' : 'danger'" size="small">
              {{ { H: '偏高', L: '偏低', C: '危急', N: '正常' }[row.abnormalFlag] || row.abnormalFlag }}
            </el-tag>
            <el-tag v-else type="success" size="small">正常</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="examTime" label="检验时间" width="160" />
        <el-table-column prop="operator" label="操作员" width="100" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const activeTab = ref('BIOCHEM')
const loading = ref(false)
const tableData = ref([])
</script>

<style scoped lang="less">
.card-header { display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: 600; }
.tab-tip { color: #909399; font-size: 13px; padding: 12px 0; }
</style>
