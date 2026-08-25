<template>
  <el-container class="layout">
    <!-- 侧边栏 -->
    <el-aside width="220px" class="aside">
      <div class="logo">
        <span class="logo-icon">🔧</span>
        <span class="logo-text">售后工单系统</span>
      </div>
      <el-menu
        :default-active="route.path"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Monitor /></el-icon>
          <span>工作台</span>
        </el-menu-item>
        <el-menu-item index="/tickets">
          <el-icon><Document /></el-icon>
          <span>工单中心</span>
        </el-menu-item>
        <el-menu-item index="/customers">
          <el-icon><User /></el-icon>
          <span>客户管理</span>
        </el-menu-item>
        <el-menu-item index="/reports">
          <el-icon><DataAnalysis /></el-icon>
          <span>报表中心</span>
        </el-menu-item>
        <el-menu-item index="/knowledge">
          <el-icon><Collection /></el-icon>
          <span>知识库</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 右侧内容 -->
    <el-container>
      <!-- 头部 -->
      <el-header class="header">
        <div class="header-left">
          <span class="page-title">{{ route.meta.title || '' }}</span>
        </div>
        <div class="header-right">
          <el-tag type="info" size="small">{{ auth.user?.real_name || '' }}</el-tag>
          <el-button text type="danger" @click="auth.logout()">退出</el-button>
        </div>
      </el-header>

      <!-- 主内容 -->
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { Monitor, Document, User, DataAnalysis, Collection } from '@element-plus/icons-vue'

const route = useRoute()
const auth = useAuthStore()
</script>

<style scoped>
.layout {
  height: 100vh;
}

.aside {
  background-color: #304156;
  overflow-y: auto;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  font-size: 16px;
  font-weight: bold;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.logo-icon {
  font-size: 22px;
}

.header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 60px;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.main {
  background: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}
</style>
