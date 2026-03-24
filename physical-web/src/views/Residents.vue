<template>
  <div>
    <el-card>
      <template #header>
        <div style="display:flex;align-items:center;gap:8px;font-size:16px;font-weight:600">
          <el-icon color="#409EFF"><User /></el-icon>
          <span>居民信息管理</span>
        </div>
      </template>
      <el-input v-model="idCard" placeholder="输入身份证号查询居民" style="width:300px;margin-right:12px" @keyup.enter="search" clearable />
      <el-button type="primary" @click="search">查询</el-button>
      <el-divider v-if="resident" />
      <el-descriptions v-if="resident" :column="3" border>
        <el-descriptions-item label="姓名">{{ resident.name }}</el-descriptions-item>
        <el-descriptions-item label="性别">{{ resident.gender === 1 ? '男' : '女' }}</el-descriptions-item>
        <el-descriptions-item label="身份证">{{ resident.idCard }}</el-descriptions-item>
        <el-descriptions-item label="手机">{{ resident.phone }}</el-descriptions-item>
        <el-descriptions-item label="乡镇">{{ resident.town }}</el-descriptions-item>
        <el-descriptions-item label="村/社区">{{ resident.village }}</el-descriptions-item>
        <el-descriptions-item label="地址" :span="3">{{ resident.address }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/request'
const idCard = ref('')
const resident = ref(null)
async function search() {
  if (!idCard.value) { ElMessage.warning('请输入身份证号'); return }
  const res = await request.get(`/core/residents/idcard/${idCard.value}`)
  if (res.code === 200) { resident.value = res.data; ElMessage.success('查询成功') }
  else { resident.value = null }
}
</script>
