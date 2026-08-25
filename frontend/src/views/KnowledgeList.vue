<template>
  <div class="knowledge-list">
    <!-- 顶部：统计卡片 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ total }}</div>
          <div class="stat-label">知识条目</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 搜索区 -->
    <el-card style="margin-bottom:16px">
      <el-row :gutter="12" align="middle">
        <!-- 关键词搜索 -->
        <el-col :span="8">
          <el-input
            v-model="keyword"
            placeholder="输入关键词搜索标题和摘要..."
            clearable
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>

        <!-- 语义检索 -->
        <el-col :span="8">
          <el-input
            v-model="semanticQuery"
            placeholder="语义检索：输入故障描述，AI 相似匹配..."
            clearable
            @keyup.enter="handleSemanticSearch"
          >
            <template #prefix>
              <el-icon><MagicStick /></el-icon>
            </template>
          </el-input>
        </el-col>

        <!-- 分类筛选 -->
        <el-col :span="3">
          <el-select v-model="category" placeholder="分类" clearable @change="handleSearch" style="width:100%">
            <el-option label="系统故障" value="系统故障" />
            <el-option label="数据库异常" value="数据库异常" />
            <el-option label="网络异常" value="网络异常" />
            <el-option label="配置错误" value="配置错误" />
            <el-option label="功能BUG" value="功能BUG" />
            <el-option label="操作咨询" value="操作咨询" />
          </el-select>
        </el-col>

        <el-col :span="5">
          <el-space>
            <el-button type="primary" @click="handleSearch" :icon="Search">搜索</el-button>
            <el-button type="warning" @click="handleSemanticSearch" :loading="semanticLoading" :icon="MagicStick">
              语义检索
            </el-button>
          </el-space>
        </el-col>
      </el-row>

      <!-- 语义检索结果提示 -->
      <el-alert
        v-if="semanticMode"
        type="warning"
        :closable="false"
        show-icon
        style="margin-top:12px"
      >
        <template #title>
          正在展示与「{{ lastSemanticQuery }}」相似的知识条目，按相关度排序
          <el-button text size="small" @click="clearSemantic">返回全部列表</el-button>
        </template>
      </el-alert>
    </el-card>

    <!-- 知识列表 -->
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>📚 {{ semanticMode ? '相似检索结果' : '知识库列表' }}（{{ total }} 条）</span>
          <el-button type="success" size="small" @click="handleExport" :loading="exporting">
            📥 导出Excel
          </el-button>
        </div>
      </template>

      <el-table
        :data="items"
        v-loading="loading"
        stripe
        @row-click="goDetail"
        style="cursor:pointer"
        empty-text="暂无知识条目，请在工单详情页将已完成的工单「提取知识」入库"
      >
        <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
        <el-table-column label="问题描述" min-width="300" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="color:#606266;font-size:13px">{{ row.problem_description || row.summary || row.document?.substring(0, 100) || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="分类" width="100">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.category || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="标签" min-width="160">
          <template #default="{ row }">
            <el-tag
              v-for="tag in parseTags(row.tags)"
              :key="tag"
              size="small"
              style="margin-right:4px"
            >{{ tag }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="难度" width="80">
          <template #default="{ row }">
            <el-tag
              v-if="row.difficulty"
              size="small"
              :type="row.difficulty === '复杂' ? 'danger' : row.difficulty === '中等' ? 'warning' : 'success'"
            >{{ row.difficulty }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="相关度" width="90" v-if="semanticMode">
          <template #default="{ row }">
            <el-progress
              v-if="row.similarity !== undefined"
              :percentage="Math.round(row.similarity * 100)"
              :stroke-width="8"
              :color="row.similarity > 0.8 ? '#67c23a' : row.similarity > 0.5 ? '#e6a23c' : '#909399'"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click.stop="goDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div style="margin-top:16px;text-align:right" v-if="!semanticMode && total > 0">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="loadList"
          @size-change="loadList"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, MagicStick } from '@element-plus/icons-vue'
import { agentAPI } from '../api'

const router = useRouter()

const loading = ref(false)
const semanticLoading = ref(false)
const semanticMode = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const semanticQuery = ref('')
const lastSemanticQuery = ref('')
const category = ref('')
const exporting = ref(false)

async function loadList() {
  loading.value = true
  try {
    const res = await agentAPI.listKnowledge({
      keyword: keyword.value,
      category: category.value,
      page: page.value,
      page_size: pageSize.value,
    })
    items.value = res.data?.items || []
    total.value = res.data?.total || 0
  } catch (e) {
    ElMessage.error('加载知识库失败')
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
    semanticMode.value = false
  }
}

function handleSearch() {
  page.value = 1
  semanticMode.value = false
  loadList()
}

async function handleSemanticSearch() {
  const q = semanticQuery.value.trim()
  if (!q) {
    ElMessage.warning('请输入故障描述进行语义检索')
    return
  }
  semanticLoading.value = true
  lastSemanticQuery.value = q
  try {
    const res = await agentAPI.search(q, 20)
    items.value = (res.data?.items || []).map(it => ({
      id: it.id,
      title: it.title,
      summary: it.summary,
      tags: Array.isArray(it.tags) ? it.tags.join(', ') : it.tags,
      category: '',
      difficulty: '',
      similarity: it.similarity,
      ticket_id: it.ticket_id,
    }))
    total.value = items.value.length
    semanticMode.value = true
  } catch (e) {
    ElMessage.error('语义检索失败')
  } finally {
    semanticLoading.value = false
  }
}

function clearSemantic() {
  semanticQuery.value = ''
  semanticMode.value = false
  page.value = 1
  loadList()
}

function parseTags(tags) {
  if (!tags) return []
  if (Array.isArray(tags)) return tags
  return tags.split(',').map(t => t.trim()).filter(Boolean)
}

function goDetail(row) {
  router.push(`/knowledge/${row.id}`)
}

function handleExport() {
  exporting.value = true
  const params = new URLSearchParams()
  if (keyword.value) params.append('keyword', keyword.value)
  if (category.value) params.append('category', category.value)

  const token = localStorage.getItem('token')
  const url = `/api/v1/agent/knowledge/export/download?${params.toString()}`

  fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then(resp => {
      if (!resp.ok) throw new Error('导出失败')
      return resp.blob()
    })
    .then(blob => {
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `知识库_${new Date().toISOString().slice(0, 10)}.xlsx`
      a.click()
      URL.revokeObjectURL(a.href)
      ElMessage.success('导出成功')
    })
    .catch(() => ElMessage.error('导出失败'))
    .finally(() => { exporting.value = false })
}

onMounted(loadList)
</script>

<style scoped>
.stat-card { text-align: center; }
.stat-value { font-size: 28px; font-weight: bold; color: #409eff; }
.stat-label { font-size: 13px; color: #909399; margin-top: 4px; }
</style>
