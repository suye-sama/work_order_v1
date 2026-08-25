<template>
  <div class="ticket-list">
    <el-card>
      <!-- 筛选栏 -->
      <el-row :gutter="12" class="filter-row">
        <el-col :span="4">
          <el-select v-model="filters.status" placeholder="状态" clearable @change="search">
            <el-option :value="1" label="新建" />
            <el-option :value="2" label="处理中" />
            <el-option :value="3" label="待确认" />
            <el-option :value="4" label="已完成" />
            <el-option :value="5" label="已归档" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-select v-model="filters.customerId" placeholder="客户" clearable filterable @change="search">
            <el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="filters.priority" placeholder="优先级" clearable @change="search">
            <el-option :value="1" label="高" />
            <el-option :value="2" label="中" />
            <el-option :value="3" label="低" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-input v-model="filters.keyword" placeholder="搜索标题" clearable @keyup.enter="search" @clear="search">
            <template #append>
              <el-button @click="search"><el-icon><Search /></el-icon></el-button>
            </template>
          </el-input>
        </el-col>
        <el-col :span="5" style="text-align:right">
          <el-button type="primary" @click="$router.push('/dashboard')">
            <el-icon><Plus /></el-icon> 新建工单
          </el-button>
        </el-col>
      </el-row>

      <!-- 表格 -->
      <el-table :data="list" stripe v-loading="loading" @row-click="(row) => $router.push(`/tickets/${row.id}`)" style="cursor:pointer">
        <el-table-column prop="ticket_no" label="工单编号" width="160" />
        <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
        <el-table-column label="客户" width="150">
          <template #default="{ row }">{{ row.customer_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="优先级" width="80">
          <template #default="{ row }">
            <el-tag :type="prioType(row.priority)" size="small">{{ prioText(row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="处理人" width="100">
          <template #default="{ row }">{{ row.handler_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ row.create_time || '-' }}</template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pager.page"
          v-model:page-size="pager.pageSize"
          :total="pager.total"
          :page-sizes="[10, 20, 50]"
          layout="total, prev, pager, next, sizes"
          @change="search"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ticketAPI, customerAPI } from '../api'
import { Search, Plus } from '@element-plus/icons-vue'

const route = useRoute()
const loading = ref(false)
const list = ref([])
const customers = ref([])

const filters = reactive({
  status: Number(route.query.status) || null,
  customerId: null,
  priority: null,
  keyword: '',
})

const pager = reactive({ page: 1, pageSize: 20, total: 0 })

const statusText = (s) => ({ 1: '新建', 2: '处理中', 3: '待确认', 4: '已完成', 5: '已归档' }[s] || '-')
const statusType = (s) => ({ 1: 'info', 2: 'warning', 3: 'primary', 4: 'success', 5: '' }[s] || '')
const prioText = (p) => ({ 1: '高', 2: '中', 3: '低' }[p] || '-')
const prioType = (p) => ({ 1: 'danger', 2: 'warning', 3: 'info' }[p] || 'info')

async function search() {
  loading.value = true
  try {
    const params = {
      page: pager.page,
      page_size: pager.pageSize,
      ...(filters.status && { status: filters.status }),
      ...(filters.customerId && { customer_id: filters.customerId }),
      ...(filters.priority && { priority: filters.priority }),
      ...(filters.keyword && { keyword: filters.keyword }),
    }
    const res = await ticketAPI.list(params)
    list.value = res.data.records
    pager.total = res.data.total
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const custRes = await customerAPI.list({ page_size: 100 })
  customers.value = custRes.data.records
  search()
})
</script>

<style scoped>
.filter-row { margin-bottom: 16px; }
.pagination { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
