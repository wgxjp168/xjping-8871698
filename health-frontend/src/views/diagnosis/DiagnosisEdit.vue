<template>
  <div class="page-container">
    <div class="page-header">
      <el-button :icon="ArrowLeft" @click="$router.back()">返回</el-button>
      <h3>{{ isEdit ? '编辑诊断报告' : '新建诊断报告' }}</h3>
    </div>

    <el-card v-loading="loading">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="体检单ID" prop="orderId">
              <el-input-number v-model="form.orderId" :min="1" style="width:100%" :disabled="isEdit" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="健康评分">
              <el-input-number v-model="form.healthScore" :min="0" :max="100" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="风险等级">
              <el-radio-group v-model="form.riskLevel">
                <el-radio-button value="LOW">低风险</el-radio-button>
                <el-radio-button value="MEDIUM">中风险</el-radio-button>
                <el-radio-button value="HIGH">高风险</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="诊断结论" prop="conclusion">
          <el-input
            v-model="form.conclusion"
            type="textarea"
            :rows="5"
            placeholder="请详细描述诊断结论，包括各项检查结果分析..."
          />
        </el-form-item>

        <el-form-item label="健康建议">
          <el-input
            v-model="form.suggestion"
            type="textarea"
            :rows="5"
            placeholder="根据体检结果，请给出具体的健康建议和注意事项..."
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            保存报告
          </el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getDiagnosisDetail, saveDiagnosis } from '@/api/diagnosis'

const route = useRoute()
const router = useRouter()
const formRef = ref()
const loading = ref(false)
const submitting = ref(false)
const isEdit = computed(() => !!route.params.id)

const form = reactive({
  id: null, orderId: null, healthScore: 80,
  riskLevel: 'LOW', conclusion: '', suggestion: ''
})

const rules = {
  orderId: [{ required: true, message: '请填写体检单ID', trigger: 'blur' }],
  conclusion: [{ required: true, message: '请填写诊断结论', trigger: 'blur' }]
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await saveDiagnosis(form)
    ElMessage.success('保存成功')
    router.back()
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  if (isEdit.value) {
    loading.value = true
    try {
      const res = await getDiagnosisDetail(route.params.id)
      Object.assign(form, res.data)
    } finally {
      loading.value = false
    }
  }
})
</script>

<style scoped>
.page-header { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
.page-header h3 { margin: 0; font-size: 18px; }
</style>
