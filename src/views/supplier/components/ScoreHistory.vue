<template>
  <el-dialog
    :model-value="modelValue"
    title="评分历史记录"
    width="800px"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <el-table
      v-loading="loading"
      :data="historyList"
      border
      size="default"
      empty-text="暂无评分历史"
    >
      <el-table-column prop="period" label="评分周期" width="120" />
      <el-table-column label="总分" width="100">
        <template #default="{ row }">
          <el-tag :type="getLevelTagType(row.level)" size="small">
            {{ row.total_score }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="等级" width="80">
        <template #default="{ row }">
          <el-tag
            :type="getLevelTagType(row.level)"
            effect="dark"
            size="small"
          >
            {{ row.level }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="quality_score" label="质量" width="70" align="center" />
      <el-table-column prop="delivery_score" label="交期" width="70" align="center" />
      <el-table-column prop="price_score" label="价格" width="70" align="center" />
      <el-table-column prop="service_score" label="服务" width="70" align="center" />
      <el-table-column prop="note" label="备注" show-overflow-tooltip />
      <el-table-column label="评分时间" width="160">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
    </el-table>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { getLevelTagType } from '@/utils/score'

defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  historyList: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['update:modelValue'])

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN', { hour12: false })
}
</script>
