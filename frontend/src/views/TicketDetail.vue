<template>
  <div class="ticket-detail" v-loading="loading">
    <!-- 头部操作栏 -->
    <el-page-header @back="$router.push('/tickets')" :title="ticket?.ticket_no">
      <template #content>
        <span class="detail-title">{{ ticket?.title }}</span>
      </template>
      <template #extra>
        <el-space wrap>
          <el-tag :type="statusType(ticket?.status)">{{ statusText(ticket?.status) }}</el-tag>
          <el-button
            v-for="btn in availableActions"
            :key="btn.status"
            :type="btn.type"
            size="small"
            @click="changeStatus(btn.status)"
          >
            {{ btn.label }}
          </el-button>
          <el-divider direction="vertical" />
          <!-- Agent 按钮 -->
          <el-button v-if="ticket?.status === 1 || ticket?.status === 2" type="warning" size="small" :loading="agentSuggesting" @click="runSuggest">
            🔍 智能排查建议
          </el-button>
          <el-button v-if="ticket?.status === 2" type="primary" size="small" :loading="agentParsing" @click="runLogParse">
            🤖 AI解析并生成工单
          </el-button>
          <el-button type="danger" size="small" @click="deleteTicket">删除</el-button>
        </el-space>
      </template>
    </el-page-header>

    <!-- 内容区域 -->
    <el-row :gutter="16" style="margin-top:16px">
      <!-- 左侧：基本信息 + 时间线 -->
      <el-col :span="16">
        <!-- 基本信息 -->
        <el-card class="section-card">
          <template #header><span>📝 基本信息</span></template>
          <el-descriptions :column="2" size="small" border>
            <el-descriptions-item label="工单编号">{{ ticket?.ticket_no }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ statusText(ticket?.status) }}</el-descriptions-item>
            <el-descriptions-item label="客户">{{ ticket?.customer_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="优先级">
              <el-tag :type="prioType(ticket?.priority)" size="small">{{ prioText(ticket?.priority) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="问题分类">{{ ticket?.category || '-' }}</el-descriptions-item>
            <el-descriptions-item label="来源">{{ ticket?.source || '-' }}</el-descriptions-item>
            <el-descriptions-item label="处理人">{{ ticket?.handler_name || '未指派' }}</el-descriptions-item>
            <el-descriptions-item label="处理时长">{{ ticket?.duration ? ticket.duration + '分钟' : '-' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间" :span="2">{{ ticket?.create_time }}</el-descriptions-item>
            <el-descriptions-item label="问题描述" :span="2">{{ ticket?.description || '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 时间线 -->
        <el-card class="section-card">
          <template #header><span>⏱️ 处理时间线</span></template>
          <el-timeline v-if="timeline.length">
            <el-timeline-item
              v-for="item in timeline"
              :key="item.id"
              :timestamp="item.node_time"
              :type="item.ai_generated ? 'primary' : 'info'"
              placement="top"
            >
              <strong>{{ item.title }}</strong>

              <!-- Agent 建议：结构化展示 -->
              <div v-if="item.node_type === 'Agent建议' && item.content" class="suggest-timeline">
                <div v-for="(block, bi) in parseSuggestContent(item.content)" :key="bi" :class="'st-block st-' + block.type">
                  <div class="st-label">{{ block.label }}</div>
                  <div v-if="block.type === 'analysis'" class="st-text">{{ block.text }}</div>
                  <ul v-else-if="block.type === 'causes' || block.type === 'history'">
                    <li v-for="(line, li) in block.items" :key="li">{{ line }}</li>
                  </ul>
                  <div v-else-if="block.type === 'checks'" class="st-checks">
                    <div v-for="(check, ci) in block.items" :key="ci" class="st-check-item">
                      <div class="st-check-line" v-for="(cl, cli) in check" :key="cli">
                        <code v-if="cl.startsWith('命令:')" class="st-cmd">{{ cl.replace('命令:', '').trim() }}</code>
                        <span v-else>{{ cl }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 普通时间线内容 -->
              <div v-else-if="item.content" class="timeline-content">{{ item.content }}</div>

              <el-tag v-if="item.ai_generated" size="small" type="warning" style="margin-top:4px">AI 生成</el-tag>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无时间线" />
        </el-card>
      </el-col>

      <!-- 右侧：日志 + Agent 预留区 -->
      <el-col :span="8">
        <!-- 操作日志输入 -->
        <el-card class="section-card">
          <template #header><span>📋 操作日志</span></template>
          <el-input
            v-model="logText"
            type="textarea"
            :rows="6"
            placeholder="在此粘贴终端操作日志/SSH命令记录/堡垒机会话..."
          />
          <el-button type="primary" size="small" style="margin-top:8px;width:100%"
            @click="appendLog" :loading="logSending"
          >
            追加日志
          </el-button>
          <el-divider />
          <div class="raw-log" v-if="ticket?.raw_log">
            <strong>已记录日志：</strong>
            <pre>{{ ticket.raw_log }}</pre>
          </div>
        </el-card>

        <!-- Agent 分析区 -->
        <el-card class="section-card agent-card" v-loading="agentWorking">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>🤖 Agent 智能分析</span>
              <el-space>
                <!-- 待确认状态：编辑/保存按钮 -->
                <template v-if="ticket?.status === 3 && !editingAi">
                  <el-button type="primary" size="small" @click="startEditAi">
                    ✏️ 修正AI内容
                  </el-button>
                </template>
                <template v-if="ticket?.status === 3 && editingAi">
                  <el-button type="success" size="small" :loading="savingAi" @click="saveAiContent">
                    💾 保存修改
                  </el-button>
                  <el-button size="small" @click="cancelEditAi">取消</el-button>
                </template>
                <el-button
                  v-if="ticket?.status >= 3 && ticket?.status <= 5"
                  type="warning"
                  size="small"
                  :loading="agentAnalyzing"
                  @click="runAnalyze"
                >
                  📊 深度分析
                </el-button>
                <el-button
                  v-if="ticket?.status >= 3"
                  size="small"
                  :loading="reportLoading"
                  @click="generateReport"
                >
                  📄 导出报告
                </el-button>
                <el-button
                  v-if="ticket?.status >= 4"
                  type="success"
                  size="small"
                  :loading="agentExtracting"
                  @click="runExtract"
                >
                  📚 提取知识
                </el-button>
              </el-space>
            </div>
          </template>

          <!-- Agent 状态提示 -->
          <el-alert
            v-if="!ticket?.fault_summary && !agentWorking"
            type="info" :closable="false" show-icon
            title="提示"
            description="追加操作日志后，点击「AI解析并生成工单」自动分析日志并填写工单内容"
            style="margin-bottom:12px"
          />

          <!-- AI 摘要 -->
          <div v-if="ticket?.ai_summary || editingAi" class="ai-block">
            <h4>📋 AI 摘要</h4>
            <el-input
              v-if="editingAi"
              v-model="editForm.ai_summary"
              type="textarea"
              :rows="3"
              placeholder="AI 摘要"
            />
            <p v-else>{{ ticket.ai_summary }}</p>
          </div>

          <!-- 故障现象 -->
          <div v-if="ticket?.fault_summary || editingAi" class="ai-block">
            <h4>🔍 故障现象</h4>
            <el-input
              v-if="editingAi"
              v-model="editForm.fault_summary"
              type="textarea"
              :rows="3"
              placeholder="故障现象"
            />
            <p v-else>{{ ticket.fault_summary }}</p>
          </div>

          <!-- 根因分析 -->
          <div v-if="ticket?.root_cause || editingAi" class="ai-block">
            <h4>🎯 根因分析</h4>
            <el-input
              v-if="editingAi"
              v-model="editForm.root_cause"
              type="textarea"
              :rows="4"
              placeholder="根因分析"
            />
            <p v-else>{{ ticket.root_cause }}</p>
          </div>

          <!-- 解决方案 -->
          <div v-if="ticket?.solution || editingAi" class="ai-block">
            <h4>🔧 解决方案</h4>
            <el-input
              v-if="editingAi"
              v-model="editForm.solution"
              type="textarea"
              :rows="4"
              placeholder="解决方案"
            />
            <p v-else>{{ ticket.solution }}</p>
          </div>

          <!-- 操作反馈 -->
          <div v-if="agentMsg" style="margin-top:8px">
            <el-alert
              :type="agentMsgType"
              :closable="false"
              show-icon
              :title="agentMsg"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 排查建议对话框 -->
    <el-dialog
      v-model="suggestVisible"
      title="🔍 AI 排查方向建议"
      width="700px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div v-loading="agentSuggesting" element-loading-text="正在生成排查建议...">
        <!-- 加载中：进度提示 -->
        <div v-if="agentSuggesting && !suggestData" class="suggest-loading">
          <el-steps :active="suggestStepIdx" align-center finish-status="process">
            <el-step title="检索案例" description="搜索相似历史知识" />
            <el-step title="智能分析" description="LLM 推理可能原因" />
            <el-step title="生成建议" description="输出排查方向" />
          </el-steps>
        </div>

        <template v-if="suggestData">
          <!-- 综合分析 -->
          <el-alert
            type="info" :closable="false" show-icon
            :title="suggestData.brief_analysis"
            style="margin-bottom:16px"
          />

          <!-- 可能原因 -->
          <div class="suggest-section" v-if="suggestData.possible_causes?.length">
            <div class="suggest-label">🎯 可能原因</div>
            <div
              v-for="(cause, idx) in suggestData.possible_causes"
              :key="'c'+idx"
              class="suggest-item cause-item"
            >
              <span class="cause-num">{{ idx + 1 }}</span>
              <span>{{ cause }}</span>
            </div>
          </div>

          <!-- 建议检查项 -->
          <div class="suggest-section" v-if="suggestData.suggested_checks?.length">
            <div class="suggest-label">🔧 建议检查项</div>
            <div
              v-for="(check, idx) in suggestData.suggested_checks"
              :key="'s'+idx"
              class="check-card"
            >
              <div class="check-header">
                <span class="check-num">{{ idx + 1 }}</span>
                <span class="check-direction">{{ check.direction }}</span>
              </div>
              <div class="check-body">
                <div class="check-row">
                  <span class="check-key">原因：</span>
                  <span>{{ check.why }}</span>
                </div>
                <div class="check-row">
                  <span class="check-key">命令：</span>
                  <code class="check-cmd">{{ check.command }}</code>
                </div>
                <div class="check-row" v-if="check.expected_if_problem">
                  <span class="check-key">预期：</span>
                  <span class="check-expect">{{ check.expected_if_problem }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 相似案例 -->
          <div class="suggest-section" v-if="suggestData.similar_cases?.length">
            <div class="suggest-label">📚 参考历史案例</div>
            <div
              v-for="(c, idx) in suggestData.similar_cases"
              :key="'h'+idx"
              class="suggest-item history-item"
              @click="$router.push(`/knowledge/${c.id}`)"
            >
              <div style="display:flex;justify-content:space-between;align-items:center">
                <span>{{ c.title }}</span>
                <el-tag size="small" :type="c.similarity > 0.8 ? 'success' : 'warning'">
                  相似度 {{ Math.round(c.similarity * 100) }}%
                </el-tag>
              </div>
              <div style="color:#909399;font-size:12px;margin-top:2px">
                {{ (c.summary || '').substring(0, 120) }}
              </div>
            </div>
          </div>

          <el-alert
            type="warning" :closable="false" show-icon
            title="以上建议仅供排查参考，不记入工单事实数据。请根据实际排查情况追加操作日志。"
            style="margin-top:12px"
          />
        </template>
      </div>

      <template #footer>
        <el-button @click="suggestVisible = false">关闭</el-button>
        <el-button type="primary" @click="suggestVisible = false">已知晓，开始排查</el-button>
      </template>
    </el-dialog>

    <!-- 故障分析对话框 -->
    <el-dialog
      v-model="analyzeVisible"
      title="📊 故障深度分析"
      width="700px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div v-loading="agentAnalyzing" element-loading-text="正在进行深度分析...">
        <template v-if="analyzeData">
          <!-- 已知问题标记 -->
          <el-alert
            v-if="analyzeData.result?.is_known_issue"
            type="success" :closable="false" show-icon
            title="✅ 已知问题 — 历史库中存在高度相似案例，以下分析基于历史经验复用"
            style="margin-bottom:16px"
          />

          <!-- 严重程度 & 复发风险 -->
          <el-row :gutter="12" style="margin-bottom:16px">
            <el-col :span="12">
              <el-statistic title="严重程度" :value="analyzeData.result?.severity || '-'">
                <template #suffix>
                  <el-tag
                    :type="analyzeData.result?.severity === '高' ? 'danger' : analyzeData.result?.severity === '中' ? 'warning' : 'info'"
                    size="small"
                    style="margin-left:8px"
                  >
                    {{ analyzeData.result?.severity || '-' }}
                  </el-tag>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="12">
              <el-statistic title="复发风险" :value="analyzeData.result?.recurrence_risk || '-'">
                <template #suffix>
                  <el-tag
                    :type="analyzeData.result?.recurrence_risk === '高' ? 'danger' : analyzeData.result?.recurrence_risk === '中' ? 'warning' : 'success'"
                    size="small"
                    style="margin-left:8px"
                  >
                    {{ analyzeData.result?.recurrence_risk || '-' }}
                  </el-tag>
                </template>
              </el-statistic>
            </el-col>
          </el-row>

          <!-- 风险详情 -->
          <div class="suggest-section" v-if="analyzeData.result?.risk_detail">
            <div class="suggest-label">⚠️ 风险分析</div>
            <div class="analyze-text">{{ analyzeData.result.risk_detail }}</div>
          </div>

          <!-- 对比分析 -->
          <div class="suggest-section" v-if="analyzeData.result?.comparison">
            <div class="suggest-label">🔬 对比分析</div>
            <div class="analyze-text">{{ analyzeData.result.comparison }}</div>
          </div>

          <!-- 相似案例 -->
          <div class="suggest-section" v-if="analyzeData.result?.similar_cases?.length">
            <div class="suggest-label">📚 相似历史案例</div>
            <div
              v-for="(c, idx) in analyzeData.result.similar_cases"
              :key="'ac'+idx"
              class="suggest-item history-item"
            >
              <span>{{ c.title }}</span>
              <el-tag size="small" :type="(c.similarity || 0) > 0.8 ? 'success' : 'warning'" style="margin-left:8px">
                相似度 {{ Math.round((c.similarity || 0) * 100) }}%
              </el-tag>
            </div>
          </div>

          <!-- 影响版本 -->
          <div class="suggest-section" v-if="analyzeData.result?.affected_versions?.length">
            <div class="suggest-label">📦 可能受影响的版本</div>
            <el-space wrap>
              <el-tag v-for="v in analyzeData.result.affected_versions" :key="v" size="small" type="info">
                {{ v }}
              </el-tag>
            </el-space>
          </div>

          <el-divider />

          <!-- 改进建议 -->
          <div class="suggest-section" v-if="analyzeData.result?.prevention">
            <div class="suggest-label">🛡️ 短期预防措施</div>
            <div class="analyze-text">{{ analyzeData.result.prevention }}</div>
          </div>

          <div class="suggest-section" v-if="analyzeData.result?.long_term_advice">
            <div class="suggest-label">🏗️ 长期优化建议</div>
            <div class="analyze-text">{{ analyzeData.result.long_term_advice }}</div>
          </div>

          <!-- 耗时提示 -->
          <el-alert
            v-if="analyzeData.duration_ms"
            type="info" :closable="false" show-icon
            :title="`分析耗时 ${(analyzeData.duration_ms / 1000).toFixed(1)} 秒`"
            style="margin-top:12px"
          />
        </template>
      </div>

      <template #footer>
        <el-button @click="analyzeVisible = false">关闭</el-button>
        <el-button type="primary" @click="analyzeVisible = false">已知晓</el-button>
      </template>
    </el-dialog>

    <!-- 报告导出对话框 -->
    <el-dialog
      v-model="reportVisible"
      title="📄 售后处理报告"
      width="900px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div v-loading="reportLoading" element-loading-text="正在生成报告...">
        <template v-if="reportMd">
          <!-- 工具栏 -->
          <div style="margin-bottom:12px;display:flex;justify-content:space-between;align-items:center">
            <el-radio-group v-model="reportEditing" size="small">
              <el-radio-button :value="false">👁️ 预览</el-radio-button>
              <el-radio-button :value="true">✏️ 编辑</el-radio-button>
            </el-radio-group>
            <el-space>
              <el-button size="small" @click="downloadReport">📥 下载 .md</el-button>
              <el-button size="small" type="primary" @click="printReport">🖨️ 打印 PDF</el-button>
            </el-space>
          </div>

          <!-- 编辑模式 -->
          <el-input
            v-if="reportEditing"
            v-model="reportMd"
            type="textarea"
            :rows="20"
            style="font-family:'Courier New',monospace;font-size:13px"
          />

          <!-- 预览模式：简易 Markdown 渲染 -->
          <div v-else class="report-preview" v-html="renderMarkdown(reportMd)" />
        </template>
      </div>

      <template #footer>
        <el-button @click="reportVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ticketAPI, agentAPI } from '../api'

const route = useRoute()
const router = useRouter()

const ticketId = Number(route.params.id)
const loading = ref(false)
const logSending = ref(false)
const ticket = ref(null)
const timeline = ref([])
const logText = ref('')

// Agent 状态
const agentParsing = ref(false)
const agentExtracting = ref(false)
const agentSuggesting = ref(false)
const suggestVisible = ref(false)
const suggestData = ref(null)
const agentAnalyzing = ref(false)
const analyzeVisible = ref(false)
const analyzeData = ref(null)
const agentWorking = ref(false)
const agentMsg = ref('')
const agentMsgType = ref('success')

// AI 内容编辑
const editingAi = ref(false)
const savingAi = ref(false)
const editForm = ref({ fault_summary: '', root_cause: '', solution: '', ai_summary: '' })

// 报告导出
const reportMd = ref('')
const reportVisible = ref(false)
const reportEditing = ref(false)
const reportLoading = ref(false)

const statusText = (s) => ({ 1: '新建', 2: '处理中', 3: '待确认', 4: '已完成', 5: '已归档' }[s] || '-')
const statusType = (s) => ({ 1: 'info', 2: 'warning', 3: 'primary', 4: 'success', 5: '' }[s] || '')
const prioText = (p) => ({ 1: '高', 2: '中', 3: '低' }[p] || '-')
const prioType = (p) => ({ 1: 'danger', 2: 'warning', 3: 'info' }[p] || 'info')

// 状态流转规则
const statusActions = {
  1: [{ status: 2, label: '开始处理', type: 'primary' }],
  2: [
    { status: 3, label: '提交确认', type: 'success' },
    { status: 4, label: '直接完成', type: 'success' },
  ],
  3: [{ status: 4, label: '确认完成', type: 'success' }],
  4: [{ status: 5, label: '归档', type: 'info' }],
  5: [],
}

const availableActions = computed(() => {
  return statusActions[ticket.value?.status] || []
})

async function loadTicket() {
  loading.value = true
  try {
    const res = await ticketAPI.getById(ticketId)
    ticket.value = res.data
    timeline.value = res.data.timeline || []
  } catch (e) {
    ElMessage.error('加载工单失败')
  } finally {
    loading.value = false
  }
}

async function changeStatus(newStatus) {
  try {
    await ticketAPI.updateStatus(ticketId, newStatus)
    ElMessage.success('状态变更成功')
    loadTicket()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '状态变更失败')
  }
}

async function appendLog() {
  if (!logText.value.trim()) {
    ElMessage.warning('请输入操作日志')
    return
  }
  logSending.value = true
  try {
    await ticketAPI.addLog(ticketId, logText.value)
    ElMessage.success('日志已追加')
    logText.value = ''
    loadTicket()
  } catch (e) {
    ElMessage.error('日志追加失败')
  } finally {
    logSending.value = false
  }
}

// ======= Agent 调用 =======

async function runLogParse() {
  if (!ticket.value?.raw_log) {
    ElMessage.warning('请先追加操作日志')
    return
  }
  agentParsing.value = true
  agentWorking.value = true
  agentMsg.value = ''
  try {
    // Step 1: 解析日志 → 生成时间线
    await agentAPI.parseLog(ticketId)
    ElMessage.success('日志解析完成，正在生成工单...')
    await loadTicket() // 刷新时间线

    // Step 2: 自动生成工单
    await agentAPI.generateTicket(ticketId)
    ElMessage.success('AI 工单生成完成，请审核确认')
    await loadTicket() // 刷新 AI 内容
  } catch (e) {
    agentMsg.value = '处理失败: ' + (e.response?.data?.detail || e.message)
    agentMsgType.value = 'error'
  } finally {
    agentParsing.value = false
    agentWorking.value = false
  }
}

// 进度提示文本
const suggestSteps = [
  '🔍 正在检索相似历史案例...',
  '🧠 正在分析故障可能原因...',
  '📝 正在生成排查方向建议...',
]
const suggestStepIdx = ref(0)
let suggestTimer = null

async function runSuggest() {
  // 已有缓存：直接展示
  if (suggestData.value) {
    suggestVisible.value = true
    return
  }

  agentSuggesting.value = true
  suggestVisible.value = true
  suggestData.value = null
  suggestStepIdx.value = 0

  // 进度文字轮播
  suggestTimer = setInterval(() => {
    if (suggestStepIdx.value < suggestSteps.length - 1) {
      suggestStepIdx.value++
    }
  }, 2000)

  try {
    const res = await agentAPI.suggestChecks(ticketId)
    suggestData.value = res.data
    await loadTicket()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '建议生成失败')
    suggestVisible.value = false
  } finally {
    clearInterval(suggestTimer)
    suggestTimer = null
    agentSuggesting.value = false
  }
}

/**
 * 解析时间线中的 Agent 建议内容，拆分为结构化区块
 * 输入格式：
 *   【综合分析】xxx
 *   【可能原因】
 *     1. xxx
 *     2. xxx
 *   【建议检查项】
 *     1. xxx
 *        原因: xxx
 *        命令: xxx
 *     2. xxx
 *   【参考历史案例】
 *     1. xxx
 */
function parseSuggestContent(content) {
  if (!content) return []
  const blocks = []
  const lines = content.split('\n')

  let currentBlock = null

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue

    // 检测区块标题
    if (trimmed.startsWith('【综合分析】')) {
      currentBlock = { type: 'analysis', label: '📋 综合分析', text: trimmed.replace('【综合分析】', '').trim(), items: [] }
      blocks.push(currentBlock)
    } else if (trimmed.startsWith('【可能原因】')) {
      currentBlock = { type: 'causes', label: '🎯 可能原因', text: '', items: [] }
      blocks.push(currentBlock)
    } else if (trimmed.startsWith('【建议检查项】')) {
      currentBlock = { type: 'checks', label: '🔧 建议检查项', text: '', items: [] }
      blocks.push(currentBlock)
    } else if (trimmed.startsWith('【参考历史案例】')) {
      currentBlock = { type: 'history', label: '📚 参考历史案例', text: '', items: [] }
      blocks.push(currentBlock)
    } else if (currentBlock) {
      // 添加到当前区块
      if (currentBlock.type === 'checks') {
        // 检查项需要特殊处理：按序号分组
        if (/^\d+\./.test(trimmed)) {
          currentBlock.items.push([trimmed])
        } else if (currentBlock.items.length > 0) {
          currentBlock.items[currentBlock.items.length - 1].push(trimmed)
        }
      } else {
        // causes / history：每行作为一个 item
        currentBlock.items.push(trimmed)
      }
    }
  }

  return blocks
}

async function runExtract() {
  agentExtracting.value = true
  agentMsg.value = ''
  try {
    const res = await agentAPI.extractKnowledge(ticketId)
    if (res.data?.success) {
      ElMessage.success(`知识提取成功！ID: ${res.data.knowledge_id}`)
    } else {
      ElMessage.warning(res.data?.error || '知识提取失败')
    }
  } catch (e) {
    agentMsg.value = '提取失败: ' + (e.response?.data?.detail || e.message)
    agentMsgType.value = 'error'
  } finally {
    agentExtracting.value = false
  }
}

async function runAnalyze() {
  // 已有缓存：直接展示
  if (analyzeData.value) {
    analyzeVisible.value = true
    return
  }

  agentAnalyzing.value = true
  analyzeVisible.value = true
  analyzeData.value = null

  try {
    const res = await agentAPI.analyzeFault(ticketId)
    analyzeData.value = res.data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '故障分析失败')
    analyzeVisible.value = false
  } finally {
    agentAnalyzing.value = false
  }
}

// ---- AI 内容编辑 ----
function startEditAi() {
  editForm.value = {
    fault_summary: ticket.value?.fault_summary || '',
    root_cause: ticket.value?.root_cause || '',
    solution: ticket.value?.solution || '',
    ai_summary: ticket.value?.ai_summary || '',
  }
  editingAi.value = true
}

function cancelEditAi() {
  editingAi.value = false
  editForm.value = { fault_summary: '', root_cause: '', solution: '', ai_summary: '' }
}

async function saveAiContent() {
  savingAi.value = true
  try {
    await ticketAPI.update(ticketId, editForm.value)
    ElMessage.success('AI 内容已保存，请审核后点击「确认完成」提交')
    editingAi.value = false
    await loadTicket()
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    savingAi.value = false
  }
}

// ---- 报告导出 ----
async function generateReport() {
  reportLoading.value = true
  reportVisible.value = true
  reportMd.value = ''
  try {
    const res = await ticketAPI.getReport(ticketId)
    reportMd.value = typeof res === 'string' ? res : (res.data || res)
  } catch (e) {
    ElMessage.error('报告生成失败: ' + (e.response?.data?.detail || e.message))
    reportVisible.value = false
  } finally {
    reportLoading.value = false
  }
}

function downloadReport() {
  const blob = new Blob([reportMd.value], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${ticket.value?.ticket_no || 'report'}_售后报告.md`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('报告已下载')
}

function printReport() {
  const w = window.open('', '_blank', 'width=900,height=700')
  w.document.write(`<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>售后处理报告</title>
<style>
  body { font-family: 'Microsoft YaHei',sans-serif; max-width:800px; margin:40px auto; padding:0 20px; color:#333; line-height:1.8; }
  h1 { text-align:center; border-bottom:2px solid #409eff; padding-bottom:10px; }
  table { border-collapse:collapse; width:100%; margin:12px 0; }
  td,th { border:1px solid #ddd; padding:8px 12px; text-align:left; }
  th { background:#f5f7fa; }
  blockquote { border-left:4px solid #409eff; padding-left:16px; color:#606266; margin:12px 0; }
  code { background:#f5f7fa; padding:2px 6px; border-radius:3px; font-size:13px; }
  pre { background:#2d2d2d; color:#e6db74; padding:16px; border-radius:6px; overflow-x:auto; font-size:12px; line-height:1.6; }
  hr { border:none; border-top:1px solid #eee; margin:24px 0; }
  h3 { margin-top:28px; color:#303133; }
  .footer { color:#909399; font-size:12px; margin-top:32px; }
  @media print { body { margin:0; } }
</style></head>
<body>${simpleMd2Html(reportMd.value)}</body></html>`)
  w.document.close()
  setTimeout(() => w.print(), 500)
}

/**
 * 超简易 Markdown → HTML（覆盖报告中的常用语法）
 */
function simpleMd2Html(md) {
  let html = md
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  // 代码块 ```...```
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
  // 行内代码 `...`
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  // 标题
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>')
  // 引用
  html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
  // 粗体/斜体
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  // 分隔线
  html = html.replace(/^---$/gm, '<hr>')
  // 表格
  html = html.replace(/^\|(.+)\|$/gm, (line) => {
    const cells = line.split('|').filter(c => c.trim()).map(c => c.trim())
    if (cells.every(c => /^[-:]+$/.test(c))) return '' // 分隔行
    const tag = cells.length > 0 ? 'td' : 'td'
    return '<tr>' + cells.map(c => `<${tag}>${c}</${tag}>`).join('') + '</tr>'
  })
  // 包裹表格行
  html = html.replace(/(<tr>.*?<\/tr>\s*)+/g, '<table>$&</table>')
  // 段落
  html = html.replace(/\n\n/g, '</p><p>')
  html = '<p>' + html + '</p>'
  // 清理空段落和多余标签
  html = html.replace(/<p>\s*<\/p>/g, '')
  html = html.replace(/<p>(<h[123]|<table|<pre|<blockquote|<hr)/g, '$1')
  html = html.replace(/(<\/h[123]>|<\/table>|<\/pre>|<\/blockquote>|<\/hr>)<\/p>/g, '$1')
  return html
}

/**
 * 渲染 Markdown 预览（编辑框里用）
 */
function renderMarkdown(md) {
  return simpleMd2Html(md)
}

async function deleteTicket() {
  await ElMessageBox.confirm('确定要删除该工单吗？', '确认删除', { type: 'warning' })
  try {
    await ticketAPI.delete(ticketId)
    ElMessage.success('删除成功')
    router.push('/tickets')
  } catch (e) {
    // 用户取消
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

onMounted(loadTicket)
</script>

<style scoped>
.detail-title { font-size: 18px; font-weight: 600; }
.section-card { margin-bottom: 16px; }
.raw-log pre {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.agent-card { border-left: 4px solid #409eff; }
.ai-block { margin-bottom: 16px; }
.ai-block h4 { margin: 0 0 6px; font-size: 14px; color: #303133; }
.ai-block p { color: #606266; font-size: 13px; line-height: 1.7; margin: 0; padding: 8px 12px; background: #f5f7fa; border-radius: 4px; white-space: pre-wrap; }

/* 排查建议对话框 */
.suggest-section { margin-bottom: 16px; }
.suggest-label { font-size: 14px; font-weight: 600; color: #303133; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid #ebeef5; }
.suggest-item { padding: 6px 10px; border-radius: 4px; margin-bottom: 4px; }
.cause-item { display: flex; align-items: flex-start; gap: 10px; background: #ecf5ff; font-size: 13px; color: #303133; line-height: 1.7; }
.cause-num { display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; border-radius: 50%; background: #409eff; color: #fff; font-size: 11px; font-weight: 700; flex-shrink: 0; margin-top: 1px; }

.check-card { border: 1px solid #ebeef5; border-radius: 6px; padding: 12px; margin-bottom: 8px; background: #fafafa; }
.check-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.check-num { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; background: #e6a23c; color: #fff; font-size: 12px; font-weight: 700; flex-shrink: 0; }
.check-direction { font-size: 14px; font-weight: 600; color: #303133; }
.check-body { padding-left: 30px; }
.check-row { font-size: 12px; color: #606266; line-height: 1.8; margin-bottom: 2px; }
.check-key { color: #909399; }
.check-cmd { display: inline-block; background: #2d2d2d; color: #e6db74; padding: 2px 6px; border-radius: 3px; font-family: 'Courier New', monospace; font-size: 11px; }
.check-expect { color: #e6a23c; }

.history-item { background: #f5f7fa; padding: 8px 10px; border-radius: 4px; margin-bottom: 4px; cursor: pointer; transition: background 0.2s; }
.history-item:hover { background: #ecf5ff; }

/* 加载中进度提示 */
.suggest-loading { padding: 20px 0; }

/* 时间线中的 Agent 建议 */
.suggest-timeline { margin-top: 8px; font-size: 13px; }
.st-block { background: #f5f7fa; border-radius: 6px; padding: 10px 14px; margin-bottom: 6px; border-left: 3px solid #409eff; }
.st-block.st-checks { border-left-color: #e6a23c; }
.st-block.st-history { border-left-color: #67c23a; }
.st-block.st-causes { border-left-color: #f56c6c; }
.st-label { font-size: 12px; font-weight: 600; color: #303133; margin-bottom: 6px; }
.st-text { color: #606266; line-height: 1.7; }
.st-block ul { margin: 0; padding-left: 18px; }
.st-block li { color: #606266; line-height: 1.7; margin-bottom: 2px; }
.st-check-item { padding: 6px 0; border-bottom: 1px dashed #e4e7ed; }
.st-check-item:last-child { border-bottom: none; }
.st-check-line { color: #606266; line-height: 1.8; font-size: 12px; padding-left: 12px; }
.st-cmd { display: inline-block; background: #2d2d2d; color: #e6db74; padding: 1px 6px; border-radius: 3px; font-family: 'Courier New', monospace; font-size: 11px; }

/* 普通时间线内容 */
.timeline-content { color: #909399; font-size: 13px; margin-top: 4px; white-space: pre-wrap; line-height: 1.7; }

/* 故障分析弹窗 */
.analyze-text { color: #606266; font-size: 13px; line-height: 1.8; padding: 10px 14px; background: #f5f7fa; border-radius: 6px; white-space: pre-wrap; }

/* 报告预览 */
.report-preview { max-height: 500px; overflow-y: auto; padding: 16px 20px; background: #fff; border: 1px solid #ebeef5; border-radius: 6px; font-size: 14px; line-height: 1.9; color: #303133; }
.report-preview :deep(h1) { font-size: 22px; text-align: center; border-bottom: 2px solid #409eff; padding-bottom: 10px; margin-top: 0; }
.report-preview :deep(h2) { font-size: 16px; margin-top: 24px; }
.report-preview :deep(h3) { font-size: 14px; margin-top: 20px; color: #409eff; }
.report-preview :deep(table) { border-collapse: collapse; width: 100%; margin: 12px 0; }
.report-preview :deep(td) { border: 1px solid #e4e7ed; padding: 6px 12px; }
.report-preview :deep(blockquote) { border-left: 4px solid #409eff; padding: 4px 16px; margin: 12px 0; color: #606266; background: #f5f7fa; }
.report-preview :deep(code) { background: #f5f7fa; padding: 2px 6px; border-radius: 3px; font-size: 13px; }
.report-preview :deep(pre) { background: #2d2d2d; color: #e6db74; padding: 14px 18px; border-radius: 6px; overflow-x: auto; font-size: 12px; line-height: 1.7; }
.report-preview :deep(hr) { border: none; border-top: 1px solid #ebeef5; margin: 20px 0; }
.report-preview :deep(strong) { color: #303133; }
</style>
