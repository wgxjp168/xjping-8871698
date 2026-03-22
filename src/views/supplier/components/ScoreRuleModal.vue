<template>
  <el-dialog
    :model-value="modelValue"
    :title="ruleData.title || '评分规则'"
    width="600px"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="rule-content">
      <el-alert
        :title="`当前评分类型：${scoreTypeLabel}`"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      />

      <div v-if="ruleData.rules && ruleData.rules.length">
        <div
          v-for="(rule, idx) in ruleData.rules"
          :key="idx"
          class="rule-item"
        >
          <div class="rule-title">
            <el-tag size="small" type="primary">{{ rule.dimension }}</el-tag>
            <span class="rule-max">满分：{{ rule.max }}分</span>
          </div>
          <p class="rule-desc">{{ rule.description }}</p>
          <el-table
            v-if="rule.levels && rule.levels.length"
            :data="rule.levels"
            size="small"
            border
            style="margin-top: 8px"
          >
            <el-table-column prop="range" label="分值区间" width="120" />
            <el-table-column prop="label" label="等级" width="80" />
            <el-table-column prop="criteria" label="评分标准" />
          </el-table>
        </div>
      </div>

      <!-- 默认规则说明 -->
      <div v-else class="default-rule">
        <el-empty description="暂无详细评分规则，请参照维度说明打分" />
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  ruleData: {
    type: Object,
    default: () => ({ title: '评分规则', rules: [] })
  },
  scoreType: {
    type: String,
    default: 'B2B'
  }
})

defineEmits(['update:modelValue'])

const scoreTypeLabel = computed(() => {
  const map = {
    B2B: 'B2B企业采购',
    B2C_BRAND: 'B2C已定品牌',
    B2C_NOBRAND: 'B2C未定品牌'
  }
  return map[props.scoreType] || props.scoreType
})
</script>

<style scoped lang="scss">
.rule-content {
  max-height: 500px;
  overflow-y: auto;
  padding-right: 4px;
}

.rule-item {
  margin-bottom: 24px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 4px;

  &:last-child {
    margin-bottom: 0;
  }
}

.rule-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.rule-max {
  font-size: 13px;
  color: #606266;
}

.rule-desc {
  margin: 0 0 8px;
  font-size: 13px;
  color: #303133;
  line-height: 1.6;
}
</style>
