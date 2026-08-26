<template>
    <div class="login">
      <div class="loginForm">
        <h2 class="login-title">{{ $t('admin.login') }}</h2>
        <div class="form-content">
          <div class="input-group">
            <label class="input-label">{{ $t('username') }}</label>
            <el-input 
              class="login-input" 
              type="text" 
              :placeholder="$t('login.username.placeholder')" 
              v-model="userForm.username"
              size="large"
            />
          </div>
          <div class="input-group">
            <label class="input-label">{{ $t('password') }}</label>
            <el-input 
              @keyup.enter="login" 
              show-password 
              class="login-input" 
              type="password" 
              :placeholder="$t('login.password.placeholder')"
              v-model="userForm.password"
              size="large"
            />
          </div>
          
          <!-- 隐私协议 -->
          <!-- <div class="privacy">
            <el-checkbox v-model="privacy" label="true">我已阅读并同意<a href="/assets/privacy/privacy.html" target="_blank">隐私协议</a></el-checkbox>
          </div> -->
          <!-- 隐私协议END -->
          
          <div class="button-container">
            <el-button 
              class="login-button" 
              @click="login" 
              type="primary"
              size="large"
            >
              {{ $t('login') }}
            </el-button>
          </div>
        </div>
      </div>
    </div>
</template>

<script setup>
import {ref,onMounted} from 'vue'
import req,{toForm} from '@/utils/req';
import { useRouter } from 'vue-router';
import { useSiteStore } from '@/stores/site';
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const siteStore = useSiteStore()

const userForm = ref({
  username: '',
  password: ''
})

const router = useRouter()

// 登录函数
const login = ()=>{
    req.post("/api/login",toForm(userForm.value))
    .then(res=>{
        if( res.data.code == 200 ) {
            // 登录成功
            localStorage.setItem("token",res.data.data.token)
            siteStore.is_login = true;
            // 临时写入邮箱
            // 提示成功
            ElMessage.success(t('login.success'))
            // 1.5s后跳转
            setTimeout(()=>{
                router.push("/")
            },1500)
        }
        else {
            // 登录失败
            ElMessage.error(t(res.data.msg))
        }
    })
    .catch(err=>{
        console.log(err)
        // 提示错误
        ElMessage.error(t('error.occurred'))
    })
}
</script>

<style scoped>
.login {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  padding: 2rem;
  box-sizing: border-box;
}

.loginForm {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  padding: 3rem;
  width: 100%;
  max-width: 420px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.login-title {
  text-align: center;
  margin: 0 0 3rem 0;
  font-size: 2rem;
  font-weight: 700;
  background: linear-gradient(45deg, #4facfe, #00f2fe);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
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

.login-input :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
  padding: 0 16px;
  height: 48px;
}

.login-input :deep(.el-input__wrapper:hover) {
  border-color: rgba(79, 172, 254, 0.5);
  background: rgba(255, 255, 255, 0.12);
}

.login-input :deep(.el-input__wrapper.is-focus) {
  border-color: #4facfe;
  box-shadow: 0 0 20px rgba(79, 172, 254, 0.3);
  background: rgba(255, 255, 255, 0.15);
}

.login-input :deep(.el-input__inner) {
  color: #ffffff;
  font-size: 1rem;
  height: 100%;
}

.login-input :deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.5);
}

.login-input :deep(.el-input__suffix) {
  color: rgba(255, 255, 255, 0.7);
}

.login-input :deep(.el-input__password) {
  color: rgba(255, 255, 255, 0.7);
}

.button-container {
  margin-top: 1rem;
}

.login-button {
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

.login-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(79, 172, 254, 0.4);
  background: linear-gradient(45deg, #4facfe, #00f2fe);
}

.login-button:active {
  transform: translateY(0);
}

:deep(.login-button:hover) {
  background: linear-gradient(45deg, #4facfe, #00f2fe);
  border-color: transparent;
}

:deep(.login-button:focus) {
  background: linear-gradient(45deg, #4facfe, #00f2fe);
  border-color: transparent;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .login {
    padding: 1rem;
  }
  
  .loginForm {
    padding: 2rem;
    max-width: 100%;
  }
  
  .login-title {
    font-size: 1.8rem;
    margin-bottom: 2rem;
  }
  
  .form-content {
    gap: 1.2rem;
  }
  
  .login-input :deep(.el-input__wrapper) {
    height: 44px;
  }
  
  .login-button {
    height: 44px;
    font-size: 1rem;
  }
}

@media (max-width: 480px) {
  .login {
    padding: 0.5rem;
  }
  
  .loginForm {
    padding: 1.5rem;
    border-radius: 15px;
  }
  
  .login-title {
    font-size: 1.6rem;
    margin-bottom: 1.5rem;
  }
  
  .input-label {
    font-size: 0.9rem;
  }
  
  .login-input :deep(.el-input__wrapper) {
    height: 42px;
    border-radius: 10px;
  }
  
  .login-button {
    height: 42px;
    border-radius: 10px;
  }
}

@media (max-width: 360px) {
  .loginForm {
    padding: 1rem;
  }
  
  .login-title {
    font-size: 1.4rem;
  }
}
</style>