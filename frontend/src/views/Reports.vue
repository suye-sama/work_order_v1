<template>
  <div class="reports">
    <!-- 概览卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6" v-for="s in summaryCards" :key="s.label">
        <el-card shadow="hover" :class="['stat-card', s.cls]">
          <div class="stat-num">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表行 -->
    <el-row :gutter="16">
      <!-- 状态分布饼图 -->
      <el-col :span="12">
        <el-card><template #header>工单状态分布</template><div ref="pieChart" style="height:300px" /></el-card>
      </el-col>
      <!-- 问题分类柱状图 -->
      <el-col :span="12">
        <el-card><template #header>问题分类统计</template><div ref="barChart" style="height:300px" /></el-card>
      </el-col>
    </el-row>

    <!-- 趋势图 -->
    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="24">
        <el-card><template #header>每日趋势（近7天）</template><div ref="lineChart" style="height:280px" /></el-card>
      </el-col>
    </el-row>

    <!-- 工作量排名 -->
    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div style="display:flex;justify-content:space-between">
              <span>工作量排名</span>
              <el-radio-group v-model="workPeriod" size="small" @change="loadWorkload">
                <el-radio-button value="week">本周</el-radio-button>
                <el-radio-button value="month">本月</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <el-table :data="workload" stripe size="small" empty-text="暂无数据">
            <el-table-column type="index" label="#" width="50" />
            <el-table-column prop="handler_name" label="工程师" />
            <el-table-column prop="completed" label="完成数" width="80" />
            <el-table-column label="平均时长" width="100">
              <template #default="{row}">{{ row.avg_duration_minutes || '-' }}分钟</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 导出 -->
      <el-col :span="12">
        <el-card>
          <template #header><span>数据导出</span></template>
          <p style="color:#909399;margin-bottom:16px">导出工单数据为 Excel 文件，支持按状态筛选</p>
          <el-select v-model="exportStatus" placeholder="全部工单" clearable style="width:160px">
            <el-option :value="1" label="新建" /><el-option :value="2" label="处理中" />
            <el-option :value="3" label="待确认" /><el-option :value="4" label="已完成" />
            <el-option :value="5" label="已归档" />
          </el-select>
          <el-button type="primary" style="margin-left:12px" @click="doExport">
            <el-icon><Download /></el-icon>导出 Excel
          </el-button>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { reportAPI } from '../api'
import { Download } from '@element-plus/icons-vue'

const pieChart = ref(null), barChart = ref(null), lineChart = ref(null)
const summary = ref({ total: 0, by_status: {}, by_priority: {}, overdue: 0 })
const categories = ref([])
const trend = ref([])
const workload = ref([])
const workPeriod = ref('week')
const exportStatus = ref(null)

const summaryCards = computed(() => [
  { label: '工单总数', value: summary.value.total, cls: 's-total' },
  { label: '处理中', value: (summary.value.by_status || {})[2] || 0, cls: 's-doing' },
  { label: '已完成', value: (summary.value.by_status || {})[4] || 0, cls: 's-done' },
  { label: '超时工单', value: summary.value.overdue || 0, cls: 's-overdue' },
])

const statusNames = { 1: '新建', 2: '处理中', 3: '待确认', 4: '已完成', 5: '已归档' }

function initPie() {
  if (!pieChart.value) return
  const chart = echarts.init(pieChart.value)
  const data = Object.entries(summary.value.by_status || {}).map(([k, v]) => ({
    name: statusNames[Number(k)] || k, value: v,
  }))
  chart.setOption({
    tooltip: { trigger: 'item' },
    series: [{ type: 'pie', radius: ['40%', '70%'], data, label: { formatter: '{b}: {c}' } }],
  })
}

function initBar() {
  if (!barChart.value) return
  const chart = echarts.init(barChart.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: categories.value.map(c => c.category) },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: categories.value.map(c => c.count), itemStyle: { color: '#409eff' } }],
  })
}

function initLine() {
  if (!lineChart.value) return
  const chart = echarts.init(lineChart.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['新建', '完成'] },
    xAxis: { type: 'category', data: trend.value.map(t => t.date) },
    yAxis: { type: 'value' },
    series: [
      { name: '新建', type: 'line', data: trend.value.map(t => t.created), smooth: true },
      { name: '完成', type: 'line', data: trend.value.map(t => t.completed), smooth: true },
    ],
  })
}

async function loadSummary() {
  const res = await reportAPI.summary()
  summary.value = res.data
  await nextTick(); initPie()
}
async function loadCategories() {
  const res = await reportAPI.categories()
  categories.value = res.data
  await nextTick(); initBar()
}
async function loadTrend() {
  const res = await reportAPI.trend(7)
  trend.value = res.data
  await nextTick(); initLine()
}
async function loadWorkload() {
  const res = await reportAPI.workload(workPeriod.value)
  workload.value = res.data
}

function doExport() {
  const params = exportStatus.value ? `?status=${exportStatus.value}` : ''
  const token = localStorage.getItem('token')
  window.open(`/api/v1/reports/export${params}`, '_blank')
}

onMounted(async () => {
  await Promise.all([loadSummary(), loadCategories(), loadTrend(), loadWorkload()])
})
</script>

<style scoped>
.stat-row { margin-bottom: 16px; }
.stat-card { text-align: center; padding: 8px 0; cursor: pointer; }
.stat-num { font-size: 32px; font-weight: bold; }
.stat-label { color: #909399; margin-top: 4px; font-size: 13px; }
.s-total .stat-num { color: #409eff; }
.s-doing .stat-num { color: #e6a23c; }
.s-done .stat-num { color: #67c23a; }
.s-overdue .stat-num { color: #f56c6c; }
</style>
