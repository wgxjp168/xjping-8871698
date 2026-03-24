<template>
  <div class="page-container">
    <el-row :gutter="20">
      <el-col :span="8" v-for="pkg in packages" :key="pkg.id">
        <el-card class="package-card" shadow="hover">
          <div class="pkg-header">
            <div class="pkg-category">{{ pkg.category }}</div>
            <div class="pkg-price">¥{{ pkg.price }}</div>
          </div>
          <h3 class="pkg-name">{{ pkg.name }}</h3>
          <p class="pkg-desc">{{ pkg.description }}</p>
          <el-divider />
          <div class="pkg-items">
            <el-tag v-for="item in pkg.items" :key="item" size="small" type="info" class="item-tag">
              {{ item }}
            </el-tag>
          </div>
          <template #footer>
            <el-button type="primary" plain style="width:100%">选择套餐</el-button>
          </template>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const packages = ref([
  {
    id: 1, name: '基础体检套餐', category: 'BASIC', price: 199,
    description: '包含基本体格检查、血常规、血糖、血压等项目，适合日常健康管理',
    items: ['身高/体重', '血压/心率', '血糖', '血常规', '体格检查']
  },
  {
    id: 2, name: '标准健康套餐', category: 'STANDARD', price: 399,
    description: '包含基础套餐全部项目，增加血脂、心电图等，适合中青年人群',
    items: ['基础套餐全部', '血脂全套', '心电图', '血氧饱和度', '肝功能']
  },
  {
    id: 3, name: '全面健康套餐', category: 'PREMIUM', price: 799,
    description: '全面体检，包含影像学检查，适合40岁以上人群',
    items: ['标准套餐全部', '胸部X光', '腹部超声', '肿瘤标志物', '骨密度']
  },
  {
    id: 4, name: '心血管专项套餐', category: 'SPECIAL', price: 599,
    description: '专注心血管系统，适合有心血管风险因素人群',
    items: ['血压监测', '心电图', '心脏超声', '血脂全套', '颈动脉超声']
  }
])
</script>

<style scoped>
.package-card {
  margin-bottom: 20px;
  transition: transform 0.2s;
}
.package-card:hover { transform: translateY(-4px); }
.pkg-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.pkg-category { font-size: 12px; color: #909399; background: #f0f2f5; padding: 2px 8px; border-radius: 4px; }
.pkg-price { font-size: 24px; font-weight: 700; color: #f56c6c; }
.pkg-name { font-size: 18px; font-weight: 600; margin: 0 0 8px; }
.pkg-desc { font-size: 13px; color: #666; line-height: 1.6; min-height: 52px; }
.pkg-items { display: flex; flex-wrap: wrap; gap: 6px; min-height: 60px; }
.item-tag { margin: 0; }
</style>
