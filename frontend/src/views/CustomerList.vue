<template>
  <div class="customer-page">
    <el-card>
      <div class="toolbar">
        <el-input v-model="keyword" placeholder="搜索客户" clearable @keyup.enter="search" style="width:240px" />
        <el-button type="primary" @click="showDialog(null)"><el-icon><Plus /></el-icon>新增客户</el-button>
      </div>
      <el-table :data="list" stripe v-loading="loading">
        <el-table-column prop="name" label="客户名称" min-width="160" />
        <el-table-column prop="region" label="地区" width="100" />
        <el-table-column prop="product_version" label="产品版本" width="100" />
        <el-table-column prop="deploy_type" label="部署方式" width="100" />
        <el-table-column prop="os" label="操作系统" width="100" />
        <el-table-column label="创建时间" width="160">
          <template #default="{row}">{{ row.create_time }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{row}">
            <el-button text type="primary" size="small" @click="showDialog(row)">编辑</el-button>
            <el-button text type="danger" size="small" @click="del(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="page" v-model:page-size="pageSize" :total="total"
        layout="total,prev,pager,next" @change="search" style="margin-top:16px;justify-content:flex-end"
      />
    </el-card>

    <!-- 弹窗 -->
    <el-dialog :title="editing?.id ? '编辑客户' : '新增客户'" v-model="dialogVisible" width="500px" @close="resetForm">
      <el-form :model="form" label-width="90px">
        <el-form-item label="客户名称" required>
          <el-input v-model="form.name" placeholder="学校/单位名称" />
        </el-form-item>
        <el-form-item label="地区">
          <el-input v-model="form.region" placeholder="省/市" />
        </el-form-item>
        <el-form-item label="产品版本">
          <el-input v-model="form.product_version" placeholder="如 V3.2.1" />
        </el-form-item>
        <el-form-item label="部署方式">
          <el-select v-model="form.deploy_type" style="width:100%">
            <el-option label="本地部署" value="本地部署" />
            <el-option label="云端部署" value="云端部署" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作系统">
          <el-select v-model="form.os" style="width:100%">
            <el-option label="Linux" value="Linux" />
            <el-option label="Windows" value="Windows" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { customerAPI } from '../api'
import { Plus } from '@element-plus/icons-vue'

const loading = ref(false), saving = ref(false)
const list = ref([]), keyword = ref(''), page = ref(1), pageSize = ref(20), total = ref(0)
const dialogVisible = ref(false), editing = ref(null)
const form = reactive({ name: '', region: '', product_version: '', deploy_type: '', os: '', description: '' })

async function search() {
  loading.value = true
  try {
    const res = await customerAPI.list({ keyword: keyword.value, page: page.value, page_size: pageSize.value })
    list.value = res.data.records; total.value = res.data.total
  } finally { loading.value = false }
}

function showDialog(row) {
  editing.value = row
  if (row) Object.assign(form, row)
  dialogVisible.value = true
}

function resetForm() {
  editing.value = null
  Object.keys(form).forEach(k => form[k] = '')
}

async function save() {
  if (!form.name) { ElMessage.warning('请输入客户名称'); return }
  saving.value = true
  try {
    if (editing.value?.id) {
      await customerAPI.update(editing.value.id, form)
      ElMessage.success('更新成功')
    } else {
      await customerAPI.create(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false; search()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally { saving.value = false }
}

async function del(id) {
  await ElMessageBox.confirm('确定删除？', '确认', { type: 'warning' })
  try { await customerAPI.delete(id); ElMessage.success('删除成功'); search() }
  catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

onMounted(search)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; margin-bottom: 16px; }
</style>
