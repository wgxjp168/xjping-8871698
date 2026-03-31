<template>
  <div>
    <el-page-header @back="$router.back()" content="体检详情" />

    <el-row :gutter="16" style="margin-top:16px">
      <!-- 左: 基本信息 + 体征 -->
      <el-col :span="10">
        <el-card title="体检基本信息" style="margin-bottom:12px">
          <template #header><b>体检基本信息</b></template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="体检单号">{{ order.orderNo }}</el-descriptions-item>
            <el-descriptions-item label="居民姓名">{{ order.residentName }}</el-descriptions-item>
            <el-descriptions-item label="身份证号">{{ order.idCard }}</el-descriptions-item>
            <el-descriptions-item label="体检日期">{{ order.checkDate }}</el-descriptions-item>
            <el-descriptions-item label="体检年度">{{ order.checkYear }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusType(order.status)" size="small">{{ statusText(order.status) }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card>
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <b>生命体征</b>
              <el-button type="primary" size="small" @click="saveVital">保存体征</el-button>
            </div>
          </template>
          <el-form :model="vital" label-width="90px" size="small">
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="身高(cm)">
                  <el-input-number v-model="vital.height" :min="0" :max="250" :precision="1" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="体重(kg)">
                  <el-input-number v-model="vital.weight" :min="0" :max="300" :precision="1" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="收缩压">
                  <el-input-number v-model="vital.systolicBp" :min="0" :max="300" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="舒张压">
                  <el-input-number v-model="vital.diastolicBp" :min="0" :max="200" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="脉搏">
                  <el-input-number v-model="vital.pulse" :min="0" :max="250" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="体温(℃)">
                  <el-input-number v-model="vital.temperature" :min="34" :max="42" :precision="1" style="width:100%" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右: 检验结果 -->
      <el-col :span="14">
        <el-card>
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <b>检验结果</b>
              <el-radio-group v-model="activeCategory" size="small">
                <el-radio-button value="">全部</el-radio-button>
                <el-radio-button value="BIOCHEM">生化</el-radio-button>
                <el-radio-button value="BLOOD">血常规</el-radio-button>
                <el-radio-button value="URINE">尿常规</el-radio-button>
                <el-radio-button value="HBA1C">糖化Hb</el-radio-button>
                <el-radio-button value="ULTRASOUND">B超</el-radio-button>
                <el-radio-button value="ECG">心电图</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <el-table :data="filteredResults" stripe size="small" max-height="500">
            <el-table-column prop="itemCode" label="项目编码" width="90" />
            <el-table-column prop="itemName" label="项目名称" width="130" />
            <el-table-column prop="itemValue" label="结果值" width="90" />
            <el-table-column prop="itemUnit" label="单位" width="80" />
            <el-table-column prop="referenceRange" label="参考范围" />
            <el-table-column prop="abnormalFlag" label="状态" width="70">
              <template #default="{ row }">
                <el-tag v-if="row.abnormalFlag === 1" type="danger" size="small">偏高</el-tag>
                <el-tag v-else-if="row.abnormalFlag === 2" type="warning" size="small">偏低</el-tag>
                <el-tag v-else type="success" size="small">正常</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="filteredResults.length === 0" description="暂无检验结果数据" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getCheckOrder, getResultsByOrder, getVitalSign, saveVitalSign } from '@/api/check'

const route = useRoute()
const order = ref({})
const results = ref([])
const vital = reactive({ orderId: null, height: null, weight: null, systolicBp: null, diastolicBp: null, pulse: null, temperature: null })

// 支持从扫码页跳转时通过 query.category 自动选中对应标签
const activeCategory = ref(route.query.category || '')

const statusText = (s) => ['待体检','体检中','已完成','已作废'][s] || '未知'
const statusType = (s) => ['info','warning','success','danger'][s] || 'info'

const filteredResults = computed(() =>
  activeCategory.value ? results.value.filter(r => r.category === activeCategory.value) : results.value
)

const saveVital = async () => {
  vital.orderId = order.value.id
  vital.residentId = order.value.residentId
  await saveVitalSign(vital)
  ElMessage.success('体征保存成功')
}

onMounted(async () => {
  const id = route.params.id
  const [orderRes, resultsRes, vitalRes] = await Promise.allSettled([
    getCheckOrder(id),
    getResultsByOrder(id),
    getVitalSign(id)
  ])
  if (orderRes.status === 'fulfilled') order.value = orderRes.value.data || orderRes.value
  if (resultsRes.status === 'fulfilled') results.value = resultsRes.value.data || resultsRes.value || []
  if (vitalRes.status === 'fulfilled' && vitalRes.value.data) {
    Object.assign(vital, vitalRes.value.data)
  }
})
</script>
