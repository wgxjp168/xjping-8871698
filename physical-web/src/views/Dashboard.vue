<template>
  <div class="dashboard">
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6" v-for="item in statCards" :key="item.label">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon" :style="{ background: item.bg }">
              <el-icon size="28" color="#fff"><component :is="item.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ item.value }}</div>
              <div class="stat-label">{{ item.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="content-row">
      <el-col :span="16">
        <el-card>
          <template #header>
            <span>今日工作概览</span>
          </template>
          <el-table :data="todayWork" stripe>
            <el-table-column prop="project" label="检验项目" />
            <el-table-column prop="total" label="总数" width="80" />
            <el-table-column prop="done" label="已完成" width="80" />
            <el-table-column prop="pending" label="待处理" width="80" />
            <el-table-column prop="rate" label="完成率" width="100">
              <template #default="{ row }">
                <el-progress :percentage="row.rate" :color="row.rate >= 80 ? '#67C23A' : '#E6A23C'" />
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>当前登录信息</span>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="医生姓名">{{ userInfo?.name }}</el-descriptions-item>
            <el-descriptions-item label="所属科室">{{ userInfo?.deptName }}</el-descriptions-item>
            <el-descriptions-item label="职称">{{ userInfo?.title || '-' }}</el-descriptions-item>
            <el-descriptions-item label="可操作项目">
              <el-tag
                v-for="code in (userInfo?.projectCodes || [])"
                :key="code"
                size="small"
                class="perm-tag"
              >{{ code }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const userInfo = computed(() => userStore.userInfo)

const statCards = ref([
  { label: '今日体检人数', value: 0, icon: 'User', bg: 'linear-gradient(135deg, #409EFF, #0d47a1)' },
  { label: 'DR待检查', value: 0, icon: 'Camera', bg: 'linear-gradient(135deg, #E6A23C, #b7591f)' },
  { label: '检验结果待录入', value: 0, icon: 'EditPen', bg: 'linear-gradient(135deg, #67C23A, #2d8a00)' },
  { label: '待同步县域', value: 0, icon: 'Upload', bg: 'linear-gradient(135deg, #909399, #555)' }
])

const todayWork = ref([
  { project: '生化检验 (BIOCHEM)', total: 0, done: 0, pending: 0, rate: 0 },
  { project: '血常规 (CBC)', total: 0, done: 0, pending: 0, rate: 0 },
  { project: '糖化血红蛋白 (HBA1C)', total: 0, done: 0, pending: 0, rate: 0 },
  { project: '尿常规 (URINE)', total: 0, done: 0, pending: 0, rate: 0 },
  { project: 'DR放射 (DR)', total: 0, done: 0, pending: 0, rate: 0 }
])
</script>

<style scoped lang="less">
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.stat-card {
  .stat-content {
    display: flex;
    align-items: center;
    gap: 16px;
    .stat-icon {
      width: 60px;
      height: 60px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .stat-value {
      font-size: 28px;
      font-weight: 700;
      color: #1a1a2e;
    }
    .stat-label {
      font-size: 13px;
      color: #666;
    }
  }
}
.perm-tag {
  margin: 2px;
}
</style>
