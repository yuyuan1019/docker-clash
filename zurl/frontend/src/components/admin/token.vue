<template>
  <div class="token-container">
    <!-- Token 使用说明 -->
    <Notice>
      <ul>
        <li>{{ $t('token.create.tips.1') }}</li>
        <li>{{ $t('token.create.tips.2') }}</li>
        <li>{{ $t('token.create.tips.3') }} <el-link href="/docs" target="_blank" type="primary" class="docs-link">/docs</el-link></li>
      </ul>
    </Notice>

    <!-- Token 信息区域 -->
    <div class="token-content">
      <!-- 没有token时显示创建按钮 -->
      <div v-if="!hasToken" class="no-token">
        <div class="empty-state">
          <el-icon class="empty-icon"><Key /></el-icon>
          <h3 class="empty-title">{{ $t('token.no.token.title') }}</h3>
          <p class="empty-desc">{{ $t('token.no.token.desc') }}</p>
          <el-button type="primary" size="large" @click="createToken" :loading="loading.create" class="create-btn">
            <el-icon><Plus /></el-icon>
            {{ $t('token.create') }}
          </el-button>
        </div>
      </div>

      <!-- 有token时显示token信息 -->
      <div v-else class="token-info">
        <div class="token-display">
          <div class="token-label">
            <el-icon><Key /></el-icon>
            <span>{{ $t('token.current') }}</span>
          </div>
          <div class="token-input-wrapper">
            <el-input
              v-model="currentToken"
              readonly
              type="password"
              show-password
              class="token-input"
              size="large"
              :placeholder="$t('token.placeholder')"
            />
          </div>
        </div>
        
        <div class="token-actions">
          <el-button type="primary" @click="copyToken" size="large">
            <el-icon><DocumentCopy /></el-icon> 
            {{ $t('token.copy') }}
          </el-button>
          <el-button type="warning" @click="changeToken" :loading="loading.change" size="large">
            <el-icon><Refresh /></el-icon>
            {{ $t('token.change') }}
          </el-button>
        </div>
      </div>
    </div>

    <el-divider />

    <!-- API 使用示例 -->
    <div class="api-example-section">
      <div class="example-header">
        <el-icon class="example-icon"><Document /></el-icon>
        <span class="example-title">{{ $t('token.api.example') }}</span>
      </div>
      <div class="example-content">
        <div class="example-card">
          <div class="example-card-header">
            <div class="header-left">
              <el-icon class="api-icon"><Link /></el-icon>
              <span>{{ $t('token.api.create.short') }}</span>
            </div>
            <el-tag type="success" size="default">POST</el-tag>
          </div>
          <div class="code-wrapper">
            <div class="code-header">
              <div class="code-info">
                <span class="code-lang">cURL</span>
                <span class="code-desc">{{ $t('token.api.curl.example') }}</span>
              </div>
              <el-button size="small" text @click="copyCode" class="copy-code-btn">
                <el-icon><DocumentCopy /></el-icon> 
                {{ $t('token.copy.code') }}
              </el-button>
            </div>
            <div class="code-content">
              <pre class="code-block" ref="codeRef">curl --location --request POST 'http://yourdomain.com/api/shorten_url' \
--header 'Authorization: Bearer token' \
--header 'Content-Type: application/json' \
--data-raw '{
    "long_url":"https://www.baidu.com",
    "short_url":"xxx"
}'</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  DocumentCopy, 
  Key, 
  Plus, 
  Refresh, 
  Document, 
  Link 
} from '@element-plus/icons-vue'
import req from '@/utils/req'
import { useBaseStore } from '@/stores/base'
import { useI18n } from 'vue-i18n'
import Notice from '../notice.vue'

const baseStore = useBaseStore()
const { t } = useI18n()
const codeRef = ref(null)

// 数据状态
const hasToken = ref(false)
const currentToken = ref('')
const loading = ref({
  create: false,
  change: false
})

// 获取Token
const getToken = async () => {
  try {
    const res = await req.get('/api/user/get_token')
    if (res.data.code === 200) {
      hasToken.value = true
      currentToken.value = res.data.data.token
    } else if (res.data.code === 404) {
      hasToken.value = false
      currentToken.value = ''
    } else {
      ElMessage.error(t(res.data.msg) || t('token.get.fail'))
    }
  } catch (error) {
    //console.error('获取Token失败:', error)
    ElMessage.error(t('token.get.fail'))
  }
}

// 创建Token
const createToken = async () => {
  loading.value.create = true
  try {
    const res = await req.get('/api/user/create_token')
    if (res.data.code === 200) {
      hasToken.value = true
      currentToken.value = res.data.data.token
      ElMessage.success(t('token.create.success'))
    } else {
      ElMessage.error(t(res.data.msg) || t('token.create.fail'))
    }
  } catch (error) {
    console.error('创建Token失败:', error)
    ElMessage.error(t('token.create.fail'))
  } finally {
    loading.value.create = false
  }
}

// 更换Token
const changeToken = async () => {
  loading.value.change = true
  try {
    const res = await req.get('/api/user/change_token')
    if (res.data.code === 200) {
      currentToken.value = res.data.data.token
      ElMessage.success(t('token.change.success'))
    } else {
      ElMessage.error(t(res.data.msg) || t('token.change.fail'))
    }
  } catch (error) {
    console.error('更换Token失败:', error)
    ElMessage.error(t('token.change.fail'))
  } finally {
    loading.value.change = false
  }
}

// 复制Token
const copyToken = () => {
  if (currentToken.value) {
    baseStore.copyText(currentToken.value)
  }
}

// 复制代码
const copyCode = () => {
  if (codeRef.value) {
    baseStore.copyText(codeRef.value.textContent)
  }
}

onMounted(() => {
  getToken()
})
</script>

<style scoped>
.token-container {
  width: 100%;
}

.docs-link {
  font-weight: 600;
}

/* Token 内容区域 */
.token-content {
  margin: 24px 0;
}

.no-token {
  padding: 20px 0;
}

.empty-state {
  text-align: center;
  padding: 60px 40px;
  background: linear-gradient(135deg, #f8f6ff 0%, #f0edff 100%);
  border-radius: 16px;
  border: 2px dashed #d0bfff;
  transition: all 0.3s ease;
}

.empty-state:hover {
  border-color: #7C3AED;
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(124, 58, 237, 0.15);
}

.empty-icon {
  font-size: 64px;
  color: #7C3AED;
  margin-bottom: 20px;
  opacity: 0.8;
}

.empty-title {
  font-size: 20px;
  color: #303133;
  margin: 0 0 12px 0;
  font-weight: 600;
}

.empty-desc {
  color: #606266;
  margin: 0 0 32px 0;
  font-size: 15px;
  line-height: 1.6;
}

.create-btn {
  padding: 14px 40px;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
  transition: all 0.3s ease;
}

.create-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(124, 58, 237, 0.4);
}

.token-info {
  padding: 20px 0;
}

.token-display {
  background: linear-gradient(135deg, #ffffff 0%, #fafbff 100%);
  border: 2px solid #e5e0ff;
  border-radius: 16px;
  padding: 32px;
  margin-bottom: 24px;
  transition: all 0.3s ease;
}

.token-display:hover {
  border-color: #7C3AED;
  box-shadow: 0 8px 25px rgba(124, 58, 237, 0.1);
}

.token-label {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  font-weight: 600;
  color: #303133;
  font-size: 16px;
}

.token-label .el-icon {
  color: #7C3AED;
  font-size: 20px;
}

.token-input-wrapper {
  width: 100%;
}

.token-input {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 14px;
}

.token-actions {
  text-align: center;
  display: flex;
  gap: 20px;
  justify-content: center;
  flex-wrap: wrap;
}

.token-actions .el-button {
  padding: 14px 32px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  min-width: 140px;
  transition: all 0.3s ease;
}

.token-actions .el-button:hover {
  transform: translateY(-2px);
}

/* API 示例样式 */
.api-example-section {
  margin-top: 32px;
}

.example-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 2px solid #f0f0f0;
}

.example-icon {
  color: #7C3AED;
  font-size: 24px;
}

.example-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.example-content {
  background: #ffffff;
  border-radius: 16px;
  border: 2px solid #f0f0f0;
  overflow: hidden;
  transition: all 0.3s ease;
}

.example-content:hover {
  border-color: #e5e0ff;
  box-shadow: 0 8px 25px rgba(124, 58, 237, 0.1);
}

.example-card-header {
  background: linear-gradient(135deg, #7C3AED 0%, #8B5CF6 100%);
  color: white;
  padding: 20px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.api-icon {
  font-size: 20px;
}

.code-wrapper {
  position: relative;
}

.code-header {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  padding: 16px 24px;
  border-bottom: 1px solid #dee2e6;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.code-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.code-lang {
  font-size: 13px;
  font-weight: 700;
  color: #495057;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.code-desc {
  font-size: 12px;
  color: #6c757d;
}

.copy-code-btn {
  color: #7C3AED;
  font-weight: 600;
  padding: 8px 16px;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.copy-code-btn:hover {
  background-color: rgba(124, 58, 237, 0.1);
}

.code-content {
  position: relative;
  overflow: hidden;
}

.code-block {
  background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
  color: #e1e5e9;
  padding: 24px;
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.7;
  overflow-x: auto;
  white-space: pre;
  border: none;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .token-container {
    padding: 0;
  }
  
  .token-display {
    padding: 24px 20px;
  }
  
  .token-actions {
    flex-direction: column;
    align-items: center;
  }
  
  .token-actions .el-button {
    width: 100%;
    max-width: 280px;
  }
  
  .example-card-header {
    padding: 16px 20px;
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .code-header {
    padding: 12px 16px;
    flex-direction: column;
    gap: 8px;
    align-items: flex-start;
  }
  
  .code-block {
    font-size: 12px;
    padding: 16px;
  }
}

:deep(.el-input__wrapper) {
  border-radius: 10px;
  border: 2px solid #e5e0ff;
  transition: all 0.3s ease;
}

:deep(.el-input__wrapper:hover) {
  border-color: #7C3AED;
}

:deep(.el-input__wrapper.is-focus) {
  border-color: #7C3AED;
  box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.1);
}

:deep(.el-button) {
  border-radius: 10px;
  transition: all 0.3s ease;
}

:deep(.el-divider) {
  margin: 32px 0;
  border-color: #e5e0ff;
}
</style>