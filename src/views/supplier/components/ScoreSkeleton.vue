<template>
  <div class="score-skeleton">
    <el-skeleton variant="text" style="width: 300px; height: 32px; margin-bottom: 16px" />

    <div class="operation-skeleton">
      <el-skeleton variant="input" style="width: 200px; margin-right: 16px" />
      <el-skeleton variant="button" style="width: 80px; margin-right: 8px" />
      <el-skeleton variant="button" style="width: 80px" />
    </div>

    <div class="card-skeleton">
      <el-skeleton variant="circle" style="width: 120px; height: 120px; margin: 0 auto 24px" />
      <el-skeleton :rows="5" style="width: 100%" />
    </div>
  </div>
</template>

<script setup>
// 骨架屏组件，无业务逻辑
</script>

<style scoped>
.score-skeleton {
  padding: 24px;
}

.operation-skeleton {
  display: flex;
  align-items: center;
  margin: 16px 0;
  padding: 16px;
  background: #fff;
  border-radius: 4px;
}

.card-skeleton {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}
</style>
