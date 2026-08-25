<template>
  <div class="dashboard">
    <!-- 顶部统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card stat-todo" @click="$router.push('/tickets?status=1')">
          <div class="stat-num">{{ todoTotal }}</div>
          <div class="stat-label">待处理工单</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card stat-doing" @click="$router.push('/tickets?status=2')">
          <div class="stat-num">{{ doingTotal }}</div>
          <div class="stat-label">处理中</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card stat-done">
          <div class="stat-num">{{ completedTotal }}</div>
          <div class="stat-label">本周已完成</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快速创建工单 -->
    <el-card class="quick-card">
      <template #header>
        <span>⚡ 快速创建工单</span>
      </template>
      <el-form :model="quickForm" inline>
        <el-form-item label="标题">
          <el-input v-model="quickForm.title" placeholder="简要描述故障" style="width:300px" />
        </el-form-item>
        <el-form-item label="客户">
          <el-select v-model="quickForm.customerId" placeholder="选择客户" style="width:200px" clearable filterable>
            <el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="quickForm.priority" style="width:120px">
            <el-option :value="1" label="高" />
            <el-option :value="2" label="中" />
            <el-option :value="3" label="低" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="quickCreate" :loading="creating">创建</el-button>
        </el-form-item>
      </el-form>
      <el-input
        v-model="quickForm.description"
        placeholder="问题描述（可选）"
        type="textarea"
        :rows="2"
        style="margin-top:8px"
      />
    </el-card>

    <!-- 我的进行中 -->
    <el-card class="list-card">
      <template #header><span>📋 我的进行中</span></template>
      <el-table :data="doingList" stripe v-loading="loading" empty-text="暂无进行中的工单">
        <el-table-column prop="ticket_no" label="编号" width="160" />
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column label="客户" width="150">
          <template #default="{ row }">{{ row.customer_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="优先级" width="80">
          <template #default="{ row }">
            <el-tag :type="prioType(row.priority)" size="small">{{ prioText(row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">{{ statusText(row.status) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button text type="primary" @click="$router.push(`/tickets/${row.id}`)">处理</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { dashboardAPI, customerAPI } from '../api'

const loading = ref(false)
const creating = ref(false)
const todoTotal = ref(0)
const doingTotal = ref(0)
const completedTotal = ref(0)
const doingList = ref([])
const customers = ref([])

const quickForm = reactive({
  title: '',
  customerId: null,
  priority: 2,
  description: '',
})

const statusText = (s) => ({ 1: '新建', 2: '处理中', 3: '待确认', 4: '已完成', 5: '已归档' }[s] || s)
const prioText = (p) => ({ 1: '高', 2: '中', 3: '低' }[p] || p)
const prioType = (p) => ({ 1: 'danger', 2: 'warning', 3: 'info' }[p] || 'info')

async function loadData() {
  loading.value = true
  try {
    const [todo, doing, completed, custData] = await Promise.all([
      dashboardAPI.todo({ page_size: 1 }),
      dashboardAPI.doing({ page_size: 10 }),
      dashboardAPI.completed({ page_size: 1 }),
      customerAPI.list({ page_size: 100 }),
    ])
    todoTotal.value = todo.data.total
    doingTotal.value = doing.data.total
    completedTotal.value = completed.data.total
    doingList.value = doing.data.records
    customers.value = custData.data.records
  } catch (e) {
    console.error('加载数据失败:', e)
  } finally {
    loading.value = false
  }
}

async function quickCreate() {
  if (!quickForm.title) {
    ElMessage.warning('请输入工单标题')
    return
  }
  creating.value = true
  try {
    await dashboardAPI.quickCreate({
      title: quickForm.title,
      customer_id: quickForm.customerId || undefined,
      priority: quickForm.priority,
      description: quickForm.description,
    })
    ElMessage.success('工单创建成功')
    quickForm.title = ''
    quickForm.description = ''
    loadData()
  } catch (e) {
    ElMessage.error('创建失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    creating.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.stat-row { margin-bottom: 16px; }
.stat-card { cursor: pointer; text-align: center; padding: 10px 0; }
.stat-num { font-size: 36px; font-weight: bold; }
.stat-label { color: #909399; margin-top: 5px; }
.stat-todo .stat-num { color: #e6a23c; }
.stat-doing .stat-num { color: #409eff; }
.stat-done .stat-num { color: #67c23a; }
.quick-card { margin-bottom: 16px; }
.list-card .el-table { margin-top: 0; }
</style>
