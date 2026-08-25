<template>
  <div class="knowledge-detail" v-loading="loading">
    <!-- 头部 -->
    <el-page-header @back="$router.push('/knowledge')" title="知识库">
      <template #content>
        <span class="detail-title">{{ detail?.title || '知识详情' }}</span>
      </template>
    </el-page-header>

    <!-- 内容 -->
    <el-row :gutter="16" style="margin-top:16px" v-if="detail">
      <!-- 左侧：知识条目详情 + 文档详情 -->
      <el-col :span="16">
        <!-- 知识条目详情 -->
        <el-card class="section-card">
          <template #header><span>📝 知识条目详情</span></template>

          <el-descriptions :column="2" size="small" border>
            <el-descriptions-item label="条目ID">{{ detail.id }}</el-descriptions-item>
            <el-descriptions-item label="分类">
              <el-tag size="small" type="info">{{ detail.category || '-' }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="难度">
              <el-tag
                v-if="detail.difficulty"
                size="small"
                :type="detail.difficulty === '复杂' ? 'danger' : detail.difficulty === '中等' ? 'warning' : 'success'"
              >{{ detail.difficulty }}</el-tag>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item label="关联工单">
              <el-link v-if="detail.ticket_id" type="primary" @click="$router.push(`/tickets/${detail.ticket_id}`)">
                #{{ detail.ticket_id }}
              </el-link>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item label="标签" :span="2">
              <el-tag
                v-for="tag in tags"
                :key="tag"
                size="small"
                style="margin-right:4px"
              >{{ tag }}</el-tag>
              <span v-if="!tags.length">-</span>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 文档详情（四段式） -->
        <el-card class="section-card" v-if="hasDocDetail">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>📄 文档详情</span>
              <el-tag size="small" type="warning">知识积累 · 问题解决参考</el-tag>
            </div>
          </template>

          <div class="doc-detail">
            <!-- 1. 问题描述 -->
            <div class="doc-block" v-if="detail.problem_description">
              <div class="doc-block-header" style="border-left-color:#409eff">
                <span class="block-num">1</span>
                <span class="block-title">问题描述</span>
              </div>
              <div class="doc-block-body">{{ detail.problem_description }}</div>
            </div>

            <!-- 2. 发生的原因 -->
            <div class="doc-block" v-if="detail.root_cause">
              <div class="doc-block-header" style="border-left-color:#e6a23c">
                <span class="block-num bg-warning">2</span>
                <span class="block-title">发生的原因</span>
              </div>
              <div class="doc-block-body">{{ detail.root_cause }}</div>
            </div>

            <!-- 3. 可能产生的现象 -->
            <div class="doc-block" v-if="detail.symptoms">
              <div class="doc-block-header" style="border-left-color:#f56c6c">
                <span class="block-num bg-danger">3</span>
                <span class="block-title">可能产生的现象</span>
              </div>
              <div class="doc-block-body">{{ detail.symptoms }}</div>
            </div>

            <!-- 4. 解决方法参考 -->
            <div class="doc-block" v-if="detail.solution">
              <div class="doc-block-header" style="border-left-color:#67c23a">
                <span class="block-num bg-success">4</span>
                <span class="block-title">解决方法参考</span>
              </div>
              <div class="doc-block-body">{{ detail.solution }}</div>

              <!-- 操作步骤 -->
              <div class="steps-box" v-if="stepsList.length">
                <div class="steps-title">操作步骤</div>
                <div
                  v-for="(step, idx) in stepsList"
                  :key="idx"
                  class="step-item"
                >
                  <span class="step-dot">{{ idx + 1 }}</span>
                  <span>{{ step }}</span>
                </div>
              </div>
            </div>

            <!-- 5. 预防措施 -->
            <div class="doc-block" v-if="detail.prevention">
              <div class="doc-block-header" style="border-left-color:#909399">
                <span class="block-num bg-info">5</span>
                <span class="block-title">预防措施</span>
              </div>
              <div class="doc-block-body">{{ detail.prevention }}</div>
            </div>
          </div>

          <!-- 原始向量文本（折叠） -->
          <el-collapse style="margin-top:12px">
            <el-collapse-item title="查看原始向量文本" name="raw">
              <pre class="doc-raw">{{ detail.document }}</pre>
            </el-collapse-item>
          </el-collapse>
        </el-card>

        <!-- 旧数据兼容：无四段式字段时显示旧格式 -->
        <el-card class="section-card" v-else-if="detail.document || detail.summary">
          <template #header><span>📄 文档详情</span></template>
          <el-alert
            type="info" :closable="false" show-icon
            title="旧格式数据"
            description="该知识条目为旧版本格式存储，仅有摘要信息。建议重新提取知识以获取完整的四段式结构。"
            style="margin-bottom:12px"
          />
          <div style="line-height:1.8;white-space:pre-wrap;color:#606266;font-size:13px">
            {{ detail.summary || detail.document || '-' }}
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：操作 + 相似知识 -->
      <el-col :span="8">
        <el-card class="section-card">
          <template #header><span>⚡ 操作</span></template>
          <el-space direction="vertical" style="width:100%">
            <el-button
              v-if="detail.ticket_id"
              type="primary"
              style="width:100%"
              @click="$router.push(`/tickets/${detail.ticket_id}`)"
            >
              📋 查看关联工单
            </el-button>
            <el-button
              style="width:100%"
              @click="handleSearchSimilar"
              :loading="similarLoading"
            >
              🔍 搜索相似知识
            </el-button>
          </el-space>
        </el-card>

        <!-- 相似知识 -->
        <el-card class="section-card" v-if="similarItems.length">
          <template #header><span>🔗 相似知识条目</span></template>
          <div
            v-for="item in similarItems"
            :key="item.id"
            class="similar-item"
            @click="$router.push(`/knowledge/${item.id}`)"
          >
            <div style="display:flex;justify-content:space-between;align-items:center">
              <strong>{{ item.title }}</strong>
              <el-tag size="small" :type="item.similarity > 0.8 ? 'success' : 'warning'">
                {{ Math.round(item.similarity * 100) }}%
              </el-tag>
            </div>
            <div style="color:#909399;font-size:12px;margin-top:4px;line-height:1.5">
              {{ (item.summary || '').substring(0, 100) }}
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 加载失败 -->
    <el-empty v-if="!loading && !detail" description="知识条目不存在或已被删除">
      <el-button type="primary" @click="$router.push('/knowledge')">返回知识库</el-button>
    </el-empty>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { agentAPI } from '../api'

const route = useRoute()
const knowledgeId = route.params.id

const loading = ref(false)
const similarLoading = ref(false)
const detail = ref(null)
const similarItems = ref([])

const tags = computed(() => {
  const t = detail.value?.tags
  if (!t) return []
  if (Array.isArray(t)) return t
  return t.split(',').map(s => s.trim()).filter(Boolean)
})

/** 是否有四段式文档详情数据 */
const hasDocDetail = computed(() => {
  const d = detail.value
  if (!d) return false
  return !!(d.problem_description || d.root_cause || d.symptoms || d.solution)
})

/** 解析操作步骤 */
const stepsList = computed(() => {
  const steps = detail.value?.steps
  if (!steps) return []
  if (Array.isArray(steps)) return steps.filter(Boolean)
  // 兼容 | 分隔的字符串
  return steps.split('|').map(s => s.trim()).filter(Boolean)
})

async function loadDetail() {
  loading.value = true
  try {
    const res = await agentAPI.getKnowledgeDetail(knowledgeId)
    detail.value = res.data
  } catch (e) {
    ElMessage.error('加载知识详情失败')
    detail.value = null
  } finally {
    loading.value = false
  }
}

async function handleSearchSimilar() {
  if (!detail.value) return
  const query = detail.value.title + ' ' + (detail.value.problem_description || detail.value.summary || '')
  similarLoading.value = true
  try {
    const res = await agentAPI.search(query, 5)
    similarItems.value = (res.data?.items || [])
      .filter(it => it.id !== knowledgeId)
      .slice(0, 5)
  } catch (e) {
    ElMessage.error('相似搜索失败')
  } finally {
    similarLoading.value = false
  }
}

onMounted(loadDetail)
</script>

<style scoped>
.detail-title { font-size: 18px; font-weight: 600; }
.section-card { margin-bottom: 16px; }

/* 四段式文档详情 */
.doc-detail {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.doc-block {
  margin-bottom: 16px;
}

.doc-block:last-child {
  margin-bottom: 0;
}

.doc-block-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-left: 4px solid #409eff;
  padding-left: 12px;
  margin-bottom: 8px;
}

.block-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}
.bg-warning { background: #e6a23c; }
.bg-danger  { background: #f56c6c; }
.bg-success { background: #67c23a; }
.bg-info    { background: #909399; }

.block-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.doc-block-body {
  padding: 12px 16px;
  background: #fafafa;
  border-radius: 6px;
  font-size: 13px;
  color: #606266;
  line-height: 1.9;
  white-space: pre-wrap;
  word-break: break-word;
}

/* 操作步骤 */
.steps-box {
  margin-top: 12px;
  padding: 12px 16px;
  background: #f0f9eb;
  border-radius: 6px;
  border: 1px solid #e1f3d8;
}

.steps-title {
  font-size: 13px;
  font-weight: 600;
  color: #67c23a;
  margin-bottom: 8px;
}

.step-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 6px 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
}

.step-dot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #67c23a;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 2px;
}

/* 原始文本 */
.doc-raw {
  background: #f5f7fa;
  padding: 10px 14px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 240px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.6;
  margin: 0;
}

/* 相似知识 */
.similar-item {
  padding: 10px 12px;
  border-radius: 6px;
  background: #f5f7fa;
  margin-bottom: 8px;
  cursor: pointer;
  transition: background 0.2s;
}
.similar-item:hover {
  background: #ecf5ff;
}
</style>
