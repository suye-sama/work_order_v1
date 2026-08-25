<template>
  <div class="login-page">
    <div class="login-card">
      <h2>🔧 售后工单系统</h2>
      <p class="sub">轻量化 · 智能化 · 登录</p>
      <el-form ref="formRef" :model="form" :rules="rules" size="large">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            prefix-icon="Lock"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleLogin" style="width:100%">
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form-item>
      </el-form>
      <p class="hint">默认账号: admin / admin123 或 engineer / engineer123</p>
      <p class="error" v-if="errorMsg">{{ errorMsg }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const formRef = ref(null)
const loading = ref(false)
const errorMsg = ref('')

const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  errorMsg.value = ''
  try {
    await auth.login(form.username, form.password)
    router.push('/dashboard')
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || '登录失败，请检查用户名和密码'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e3c72, #2a5298);
}

.login-card {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.2);
}

.login-card h2 {
  text-align: center;
  margin: 0 0 8px;
  color: #303133;
}

.sub {
  text-align: center;
  color: #909399;
  margin: 0 0 30px;
  font-size: 13px;
}

.hint {
  text-align: center;
  color: #c0c4cc;
  font-size: 12px;
  margin-top: 10px;
}

.error {
  text-align: center;
  color: #f56c6c;
  font-size: 13px;
  margin-top: 8px;
}
</style>
