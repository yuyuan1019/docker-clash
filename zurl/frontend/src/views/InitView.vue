<template>
  <div class="init">
    <div class="initForm">
      <h2 class="init-title">{{ $t('system.init') }}</h2>
      <p class="init-subtitle">{{ $t('create.admin.account') }}</p>
      
      <div class="form-content">
        <div class="input-group">
          <label class="input-label">{{ $t('username') }}</label>
          <el-input 
            class="init-input" 
            type="text" 
            :placeholder="$t('init.username.placeholder')" 
            v-model="userForm.username"
            size="large"
          />
        </div>
        
        <div class="input-group">
          <label class="input-label">{{ $t('email') }}</label>
          <el-input 
            class="init-input" 
            type="text" 
            :placeholder="$t('init.email.placeholder')" 
            v-model="userForm.email"
            size="large"
          />
        </div>
        
        <div class="input-group">
          <label class="input-label">{{ $t('password') }}</label>
          <el-input 
            show-password 
            class="init-input" 
            type="password" 
            :placeholder="$t('init.password.placeholder')"
            v-model="userForm.password"
            size="large"
          />
        </div>
        
        <div class="input-group">
          <label class="input-label">{{ $t('repeat.password') }}</label>
          <el-input 
            @keyup.enter="init" 
            show-password 
            class="init-input" 
            type="password" 
            :placeholder="$t('init.repeat.password.placeholder')"
            v-model="userForm.repeat_password"
            size="large"
          />
        </div>
        
        <div class="button-container">
          <el-button 
            class="init-button" 
            @click="init" 
            type="primary"
            size="large"
          >
            {{ $t('init.system') }}
          </el-button>
        </div>
        
        <!-- <div class="login-link">
          <router-link to="/login">已有账户？点击登录</router-link>
        </div> -->
      </div>
    </div>
  </div>
</template>

<script setup>
import {ref,onMounted} from 'vue'
import {useRouter} from 'vue-router'
import req from '@/utils/req';
import { ElMessage } from 'element-plus';
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const router = useRouter()
const userForm = ref({
  username: '',
  email: '',
  password: '',
  repeat_password: ''
})

const init = () => {
  // 用户名不能为空
  if (!userForm.value.username) {
    return ElMessage.error(t('username.required'));
  }
  // 要求用户名必须是小写
  if (!/^[a-z0-9]+$/.test(userForm.value.username)) {
    return ElMessage.error(t('username.lowercase.only'));
  }

  // 邮箱不能为空，且必须是正确的邮箱格式
  if (!userForm.value.email || !/\S+@\S+\.\S+/.test(userForm.value.email)) {
    return ElMessage.error(t('email.required'));
  }

  // 密码不能为空
  if (!userForm.value.password) {
    return ElMessage.error(t('password.required'));
  }

  // 判断用户输入的密码是否一致
  if (userForm.value.password !== userForm.value.repeat_password) {
    
    return ElMessage.error(t('password.mismatch'));
  }

  const formData = {
    username: userForm.value.username,
    email: userForm.value.email,
    password: userForm.value.password
  }

  // 继续请求后端
  req.post('/api/user/init', formData).then(res => {
    if (res.data.code === 200) {
      ElMessage.success(t('init.success'));
      // 2s后跳转
      setTimeout(() => {
        router.push('/login');
      }, 2000);
      // router.push('/login');
    } else {
      ElMessage.error(t(res.data.msg));
    }
  })
  .catch(err => {
    console.error(err);
    ElMessage.error(t('init.failed'));
  });
}
</script>

<style scoped>
.init {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  padding: 2rem;
  box-sizing: border-box;
}

.initForm {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  padding: 3rem;
  width: 100%;
  max-width: 450px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.init-title {
  text-align: center;
  margin: 0 0 1rem 0;
  font-size: 2rem;
  font-weight: 700;
  background: linear-gradient(45deg, #4facfe, #00f2fe);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.init-subtitle {
  text-align: center;
  margin: 0 0 3rem 0;
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.7);
}

.form-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.input-label {
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.95rem;
  font-weight: 500;
  margin: 0;
}

.init-input :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
  padding: 0 16px;
  height: 48px;
}

.init-input :deep(.el-input__wrapper:hover) {
  border-color: rgba(79, 172, 254, 0.5);
  background: rgba(255, 255, 255, 0.12);
}

.init-input :deep(.el-input__wrapper.is-focus) {
  border-color: #4facfe;
  box-shadow: 0 0 20px rgba(79, 172, 254, 0.3);
  background: rgba(255, 255, 255, 0.15);
}

.init-input :deep(.el-input__inner) {
  color: #ffffff;
  font-size: 1rem;
  height: 100%;
}

.init-input :deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.5);
}

.init-input :deep(.el-input__suffix) {
  color: rgba(255, 255, 255, 0.7);
}

.init-input :deep(.el-input__password) {
  color: rgba(255, 255, 255, 0.7);
}

.button-container {
  margin-top: 1rem;
}

.init-button {
  width: 100%;
  height: 48px;
  background: linear-gradient(45deg, #4facfe, #00f2fe);
  border: none;
  border-radius: 12px;
  font-size: 1.1rem;
  font-weight: 600;
  transition: all 0.3s ease;
  color: #ffffff;
}

.init-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(79, 172, 254, 0.4);
  background: linear-gradient(45deg, #4facfe, #00f2fe);
}

.init-button:active {
  transform: translateY(0);
}

:deep(.init-button:hover) {
  background: linear-gradient(45deg, #4facfe, #00f2fe);
  border-color: transparent;
}

:deep(.init-button:focus) {
  background: linear-gradient(45deg, #4facfe, #00f2fe);
  border-color: transparent;
}

.login-link {
  text-align: center;
  margin-top: 1rem;
}

.login-link a {
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  font-size: 0.9rem;
  transition: color 0.3s ease;
}

.login-link a:hover {
  color: #4facfe;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .init {
    padding: 1rem;
  }
  
  .initForm {
    padding: 2rem;
    max-width: 100%;
  }
  
  .init-title {
    font-size: 1.8rem;
    margin-bottom: 0.8rem;
  }
  
  .init-subtitle {
    font-size: 0.9rem;
    margin-bottom: 2rem;
  }
  
  .form-content {
    gap: 1.2rem;
  }
  
  .init-input :deep(.el-input__wrapper) {
    height: 44px;
  }
  
  .init-button {
    height: 44px;
    font-size: 1rem;
  }
}

@media (max-width: 480px) {
  .init {
    padding: 0.5rem;
  }
  
  .initForm {
    padding: 1.5rem;
    border-radius: 15px;
  }
  
  .init-title {
    font-size: 1.6rem;
    margin-bottom: 0.5rem;
  }
  
  .init-subtitle {
    font-size: 0.85rem;
    margin-bottom: 1.5rem;
  }
  
  .input-label {
    font-size: 0.9rem;
  }
  
  .init-input :deep(.el-input__wrapper) {
    height: 42px;
    border-radius: 10px;
  }
  
  .init-button {
    height: 42px;
    border-radius: 10px;
  }
}

@media (max-width: 360px) {
  .initForm {
    padding: 1rem;
  }
  
  .init-title {
    font-size: 1.4rem;
  }
  
  .init-subtitle {
    font-size: 0.8rem;
  }
}
</style>