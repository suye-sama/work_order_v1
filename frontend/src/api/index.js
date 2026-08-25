/**
 * Axios 封装 — 自动挂 Token，统一错误处理
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/',
  timeout: 30000,
})

// 请求拦截器：自动附加 JWT Token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一处理 401 跳转登录
api.interceptors.response.use(
  (resp) => resp.data, // 直接返回 data，组件里少写一层 .data
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ---- 认证 API ----
export const authAPI = {
  login: (username, password) =>
    api.post('/api/v1/auth/login', { username, password }),
  getMe: () => api.get('/api/v1/auth/me'),
}

// ---- 工单 API ----
export const ticketAPI = {
  list: (params) => api.get('/api/v1/tickets', { params }),
  getById: (id) => api.get(`/api/v1/tickets/${id}`),
  create: (data) => api.post('/api/v1/tickets', data),
  update: (id, data) => api.put(`/api/v1/tickets/${id}`, data),
  delete: (id) => api.delete(`/api/v1/tickets/${id}`),
  updateStatus: (id, status) =>
    api.post(`/api/v1/tickets/${id}/status`, { status }),
  assign: (id, handlerId) =>
    api.post(`/api/v1/tickets/${id}/assign`, { handler_id: handlerId }),
  addLog: (id, logText) =>
    api.post(`/api/v1/tickets/${id}/log`, null, { params: { log_text: logText } }),
  getReport: (id) =>
    api.get(`/api/v1/tickets/${id}/report`, { responseType: 'text' }),
}

// ---- 客户 API ----
export const customerAPI = {
  list: (params) => api.get('/api/v1/customers', { params }),
  getById: (id) => api.get(`/api/v1/customers/${id}`),
  create: (data) => api.post('/api/v1/customers', data),
  update: (id, data) => api.put(`/api/v1/customers/${id}`, data),
  delete: (id) => api.delete(`/api/v1/customers/${id}`),
}

// ---- 报表 API ----
export const reportAPI = {
  summary: () => api.get('/api/v1/reports/summary'),
  categories: () => api.get('/api/v1/reports/categories'),
  workload: (period) => api.get('/api/v1/reports/workload', { params: { period } }),
  trend: (days) => api.get('/api/v1/reports/trend', { params: { days } }),
}

// ---- 工作台 API ----
export const dashboardAPI = {
  todo: (params) => api.get('/api/v1/dashboard/todo', { params }),
  doing: (params) => api.get('/api/v1/dashboard/doing', { params }),
  completed: (params) => api.get('/api/v1/dashboard/completed', { params }),
  quickCreate: (params) => api.post('/api/v1/dashboard/quick-ticket', null, { params }),
}

// ---- Agent API（超时 120 秒，LLM 调用较慢）----
const agentApi = axios.create({
  baseURL: '/',
  timeout: 120000,
})
agentApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
agentApi.interceptors.response.use(
  (resp) => resp.data,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const agentAPI = {
  parseLog: (ticketId) =>
    agentApi.post(`/api/v1/agent/log-parse?ticket_id=${ticketId}`),
  generateTicket: (ticketId) =>
    agentApi.post(`/api/v1/agent/generate?ticket_id=${ticketId}`),
  extractKnowledge: (ticketId) =>
    agentApi.post(`/api/v1/agent/extract?ticket_id=${ticketId}`),
  search: (query, topK = 5) =>
    agentApi.get('/api/v1/agent/search', { params: { q: query, top_k: topK } }),
  // 知识库
  listKnowledge: (params = {}) =>
    api.get('/api/v1/agent/knowledge', { params }),
  getKnowledgeDetail: (id) =>
    api.get(`/api/v1/agent/knowledge/${id}`),
  // 排查建议
  suggestChecks: (ticketId) =>
    agentApi.post(`/api/v1/agent/suggest/${ticketId}`),
  // 故障分析
  analyzeFault: (ticketId) =>
    agentApi.post(`/api/v1/agent/analyze?ticket_id=${ticketId}`),
}

export default api
