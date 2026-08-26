<template>
    <div class="admin">
        <div class="common-layout">
            <el-container>
            <el-aside class="left">
                <!-- 标题或者logo部分 -->
                <div class="logo" @click="router.push('/')">
                    <h1>Zurl</h1>
                </div>
                <!-- 标题或者logo部分END -->

                <!-- 菜单部分 -->
                <div class="menus">
                    <div style="margin-top: 1em;"></div>
                    <el-menu
                        :default-active="currentIndex"
                    >
                        <el-menu-item @click="router.push('/admin/list')" index="list">
                            <el-icon><Link /></el-icon>
                            <span>{{ $t('link.list') }}</span>
                        </el-menu-item>

                        <!-- <el-menu-item index="embedding">
                            <el-icon><Tickets /></el-icon>
                            <span>向量数据</span>
                        </el-menu-item> -->

                        

                        <!-- <el-menu-item @click="router.push('/admin/setting')" index="setting">
                            <el-icon><setting /></el-icon>
                            <span>参数设置</span>
                        </el-menu-item> -->

                        <el-menu-item @click="router.push('/admin/migration')" index="migration">
                            <el-icon><DArrowRight /></el-icon>
                            <span>{{ $t('data.move') }}</span>
                        </el-menu-item>

                        <el-menu-item @click="router.push('/admin/setting')" index="setting">
                            <el-icon><Setting /></el-icon>
                            <span>{{ $t('site.settings') }}</span>
                        </el-menu-item>

                        <el-menu-item @click="router.push('/admin/token')" index="token">
                            <el-icon><Key /></el-icon>
                            <span>API Token</span>
                        </el-menu-item>


                        <el-menu-item v-if="locale === 'zh'" @click="router.push('/admin/about')" index="about">
                            <el-icon><User /></el-icon>
                            <span>{{ $t('about.us') }}</span>
                        </el-menu-item>

                    </el-menu>
                </div>
                <!-- 菜单部分END -->

                <!-- 版本部分 -->
                <div class="version">
                    <el-text class="mx-1" type="info">v{{ version }}</el-text>
                </div>
                <!-- 版本部分END -->
            </el-aside>
            <el-container>
                <el-header>
                    <div class="header">
                        <div class="l-header">
                            <div class="menu">
                                <div class="item">
                                    <el-link href="/">{{ $t('home') }}</el-link>
                                </div>
                                <div class="item">
                                    <el-link href="https://github.com/helloxz/zurl" target="_blank">{{ $t('help.document') }}</el-link>
                                </div>

                                <div class="item">
                                    <el-link href="/docs" target="_blank">API</el-link>
                                </div>

                                <div class="item">
                                    <el-link href="https://github.com/helloxz/zurl" :title="$t('go.to.github')" target="_blank">Github</el-link>
                                </div>
                            </div>
                        </div>
                        <div class="r-header">
                            
                            <!-- 显示邮箱 -->
                            <!-- <el-text class="mx-1 email">{{ siteStore.username }}</el-text> -->
                            <!-- 显示邮箱END -->
                            
                            <!-- 语言切换按钮 -->
                            <div class="language-switch" @click="toggleLanguage" :title="getLanguageSwitchTitle()">
                                <svg class="language-icon" width="18" height="18" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M28.2857 37H39.7143M42 42L39.7143 37L42 42ZM26 42L28.2857 37L26 42ZM28.2857 37L34 24L39.7143 37H28.2857Z" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M16 6L17 9" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M6 11H28" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M10 16C10 16 11.7895 22.2609 16.2632 25.7391C20.7368 29.2174 28 32 28 32" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M24 11C24 11 22.2105 19.2174 17.7368 23.7826C13.2632 28.3478 6 32 6 32" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                                </svg>
                                <span class="language-text">{{ getTargetLanguageText() }}</span>
                            </div>
                            <!-- 语言切换按钮END -->
                            
                            <!-- 头像部分 -->
                            <div class="avatar" style="cursor: pointer;">
                                <el-dropdown placement="bottom-end">
                                    <span class="el-dropdown-link">
                                        <el-avatar :size="36" loading="lazy" :src="avatar"></el-avatar>
                                        <i class="el-icon-arrow-down el-icon--right"></i>
                                    </span>
                                    <template #dropdown>
                                        <div class="user-info">
                                            <div class="info-item">
                                                <el-icon><User /></el-icon>
                                                <span>{{ siteStore.username }}</span>
                                            </div>
                                            <div class="info-item">
                                                <el-icon><Message /></el-icon>
                                                <span>{{ siteStore.email }}</span>
                                            </div>
                                        </div>

                                        <el-dropdown-menu>
                                            <el-dropdown-item @click="showChangePasswordDialog">{{ $t('user.change.password', '修改密码') }}</el-dropdown-item>
                                            <el-dropdown-item @click="logout">{{ $t('user.logout') }}</el-dropdown-item>
                                        </el-dropdown-menu>
                                    </template>
                                </el-dropdown>
                            </div>
                            <!-- 头像部分END -->
                        </div>
                    </div>
                </el-header>
                <el-main>
                    <!-- 内容主体区域 -->
                    <div class="content">
                        <component :is="currentTab"></component>
                    </div>
                    <!-- 内容主体区域END -->
                </el-main>
                <el-footer class="footer">
                    <div>
                        <div class="footer-content">
                            <span class="copyright">Copyright Ⓒ 2025</span>
                            <span class="separator">•</span>
                            <span>Powered by <a target="_blank" href="https://github.com/helloxz/zurl" class="footer-link">Zurl</a></span>
                        </div>
                    </div>
                </el-footer>
            </el-container>
            </el-container>
        </div>

        <!-- 修改密码弹窗 -->
        <el-dialog 
            v-model="changePasswordDialogVisible" 
            :title="$t('user.change.password', '修改密码')"
            width="400px"
            :before-close="handleClosePasswordDialog"
        >
            <el-form 
                ref="changePasswordFormRef" 
                :model="changePasswordForm" 
                :rules="changePasswordRules"
                label-width="100px"
                label-position="top"
            >
                <el-form-item :label="$t('user.old.password', '旧密码')" prop="oldPassword">
                    <el-input 
                        v-model="changePasswordForm.oldPassword" 
                        type="password" 
                        show-password
                        :placeholder="$t('user.enter.old.password', '请输入旧密码')"
                    />
                </el-form-item>
                <el-form-item :label="$t('user.new.password', '新密码')" prop="newPassword">
                    <el-input 
                        v-model="changePasswordForm.newPassword" 
                        type="password" 
                        show-password
                        :placeholder="$t('user.enter.new.password', '请输入新密码')"
                    />
                </el-form-item>
                <el-form-item :label="$t('user.confirm.password', '确认密码')" prop="confirmPassword">
                    <el-input 
                        v-model="changePasswordForm.confirmPassword" 
                        type="password" 
                        show-password
                        :placeholder="$t('user.confirm.new.password', '请确认新密码')"
                    />
                </el-form-item>
            </el-form>
            <template #footer>
                <span class="dialog-footer">
                    <el-button @click="changePasswordDialogVisible = false">{{ $t('cancel', '取消') }}</el-button>
                    <el-button 
                        type="primary" 
                        @click="handleChangePassword"
                        :loading="changePasswordLoading"
                    >
                        {{ $t('confirm', '确定') }}
                    </el-button>
                </span>
            </template>
        </el-dialog>
    </div>
</template>

<script setup>
import {
    Setting,
    DArrowRight,
    Link,
    Notebook,
    User,
    Message,
    Key
} from '@element-plus/icons-vue'
import { ref,onMounted,shallowRef } from 'vue'
import { useRouter,useRoute } from 'vue-router'
import list from '@/components/admin/list.vue';
import settingCom from '@/components/admin/setting.vue';
import about from '@/components/admin/about.vue';
import token from '@/components/admin/token.vue';
import migration from '@/components/admin/migration.vue';
import { useSiteStore } from '@/stores/site';
import md5 from 'md5';
import Github from '@/assets/github.svg'
import { ElMessage } from 'element-plus';
import req from '@/utils/req';
import { useI18n } from 'vue-i18n'

const { t, locale } = useI18n()

const currentIndex = ref("list")
// 根据路由获取的名称来改变组件
const route = useRoute()
const router = useRouter()
const currentTab = shallowRef(list) // 使用 ref 来保持响应式
const siteStore = useSiteStore()
// 系统版本
const version = ref("")
// 头像地址
const avatar = ref("")

const changeTab = ()=>{
    let name = route.params.name
    // console.log(name)
    switch(name){
        case 'list':
            currentTab.value = list
            break
        case 'setting':
            currentTab.value = settingCom
            break
        case 'about':
            currentTab.value = about
            break
        case 'migration':
            currentTab.value = migration
            break
        case 'token':
            currentTab.value = token
            break
        default:
            currentTab.value = list
    }
    currentIndex.value = name
    // console.log(currentTab.value)
}

// 退出登录
const logout = ()=>{
    // 弹出提示
    ElMessage.success("您已退出！")
    // 请求退出API
    req.get("/api/user/logout")
        .then(res=>{
            // 只管请求，不管结果。
        })
        .catch(err=>{
            console.error(err)
            // ElMessage.error("退出失败，请稍后再试")
        })
    // 2s后执行
    setTimeout(()=>{
        localStorage.removeItem("token")
        sessionStorage.removeItem("app_info")
        router.push("/login")
    },2000)
}

// 检测用户是否登录
const isLogin = ()=>{
    req.get("/api/user/is_login")
    .then(res=>{
        if( res.data.code == 200) {
            return;
        }
    })
    .catch(err=>{
        if (err.response) {
            if (err.response.status === 401) {
                // 提示错误
                ElMessage.error(t('no.login.msg'))
                router.push("/login")
            }
        }
    })
}

onMounted(()=>{
    // 如果没有登录，跳转到登录页面
    siteStore.checkLogin()
    .then(()=>{
        if(!siteStore.is_login) {
            router.push("/login")
            return;
        }
    })
    changeTab()
    siteStore.getAppInfo()
    .then(res=>{
        version.value = siteStore.app_info["version"]
        avatar.value = 'https://gravatar.loli.net/avatar/' + md5(siteStore.app_info["email"])
    })
})

// 监听路由变化
router.afterEach((to, from) => {
    changeTab()
})

// 处理语言切换
const toggleLanguage = () => {
    const currentLang = localStorage.getItem('user_language') || 'en'
    const newLang = currentLang === 'zh' ? 'en' : 'zh'
    siteStore.switchLanguage(newLang)
}

// 获取目标语言文本（要切换到的语言）
const getTargetLanguageText = () => {
    const currentLang = localStorage.getItem('user_language') || 'en'
    return currentLang === 'zh' ? 'English' : '中文'
}

// 获取语言切换的title提示
const getLanguageSwitchTitle = () => {
    const currentLang = localStorage.getItem('user_language') || 'en'
    return currentLang === 'zh' ? 'Switch to English' : 'Switch to Chinese'
}

const email = ref(sessionStorage.getItem("email"))

// 修改密码相关
const changePasswordDialogVisible = ref(false)
const changePasswordFormRef = ref()
const changePasswordLoading = ref(false)
const changePasswordForm = ref({
    oldPassword: '',
    newPassword: '',
    confirmPassword: ''
})

// 修改密码表单验证规则
const changePasswordRules = ref({
    oldPassword: [
        { required: true, message: t('user.enter.old.password', '请输入旧密码'), trigger: 'blur' }
    ],
    newPassword: [
        { required: true, message: t('user.enter.new.password', '请输入新密码'), trigger: 'blur' },
        { min: 6, message: t('user.password.min.length', '密码长度至少6位'), trigger: 'blur' }
    ],
    confirmPassword: [
        { required: true, message: t('user.confirm.new.password', '请确认新密码'), trigger: 'blur' },
        {
            validator: (rule, value, callback) => {
                if (value !== changePasswordForm.value.newPassword) {
                    callback(new Error(t('user.password.not.match', '两次密码输入不一致')))
                } else {
                    callback()
                }
            },
            trigger: 'blur'
        }
    ]
})

// 显示修改密码对话框
const showChangePasswordDialog = () => {
    changePasswordDialogVisible.value = true
    // 重置表单
    changePasswordForm.value = {
        oldPassword: '',
        newPassword: '',
        confirmPassword: ''
    }
}

// 关闭修改密码对话框
const handleClosePasswordDialog = () => {
    changePasswordDialogVisible.value = false
    if (changePasswordFormRef.value) {
        changePasswordFormRef.value.resetFields()
    }
}

// 处理修改密码
const handleChangePassword = async () => {
    if (!changePasswordFormRef.value) return
    
    try {
        await changePasswordFormRef.value.validate()
        changePasswordLoading.value = true
        
        const formData = new FormData()
        formData.append('old_password', changePasswordForm.value.oldPassword)
        formData.append('new_password', changePasswordForm.value.newPassword)
        
        const response = await req.post('/api/user/change_password', formData)
        
        if (response.data.code === 200) {
            ElMessage.success(t('success'))
            changePasswordDialogVisible.value = false
            
            // 2秒后自动退出登录
            setTimeout(() => {
                logout()
            }, 2000)
        } else {
            ElMessage.error(t(response.data.msg) || t('user.password.change.failed', '密码修改失败'))
        }
    } catch (error) {
        // console.error('修改密码失败:', error)
        if (error.response && error.response.data && error.response.data.msg) {
            ElMessage.error(t(error.response.data.msg))
        } else {
            ElMessage.error(t('user.password.change.failed', '密码修改失败'))
        }
    } finally {
        changePasswordLoading.value = false
    }
}
</script>

<style scoped>
.github{
    margin-right: 26px;
    margin-left:12px;
}
.l-header .menu{
    margin-left:2em;
}
.menu .item{
    margin-right: 16px;
    cursor: pointer;
    display: inline-block;
}
.left{
    width: 200px;
    background: radial-gradient(circle, #E7DFFF, #F8F0FF); /* 从中心浅紫色向外辐射到更浅的颜色 */
    height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: sticky;
    top: 0; /* 或者其他你希望的顶部偏移量 */
    /* border-right: #E7DFFF; */
}
.version{
    height:40px;
    text-align: center;
}
.menus{
    height: calc(100% - 98px);
}
.header{
    /* background-color: #7C3AED; */
    height: 58px;
    display: flex;
    flex-direction: row;
    flex-wrap: nowrap;
    justify-content: space-between;
    align-items: center;
    
    /* border-bottom: 1px solid #EBEEF5; */
    background: radial-gradient(circle, #E7DFFF, #F8F0FF); /* 从中心浅紫色向外辐射到更浅的颜色 */
}

.content{
    width:calc(100% - 100px);
    margin-left: auto;
    margin-right: auto;
    display: flex;
    justify-content: center;
    max-width: 1200px;
    margin-top:1em;
    /* background-color: #7C3AED; */
}

.r-header{
    display: flex;
    align-items: center;
}
.email{
    margin-right: 16px;
}
.avatar{
    margin-right: 12px;
}

.logo{
    display: flex;
    flex-wrap: nowrap;
    height: 58px;
    justify-content: center;
    align-items: center;
    background: linear-gradient(135deg, #8B5CF6 0%, #7C3AED 50%, #6D28D9 100%);
    box-shadow: 0 2px 8px rgba(124, 58, 237, 0.15);
    position: relative;
}
.logo::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.3) 50%, transparent 100%);
}

.logo h1 {
    cursor: pointer;
    font-size: 26px;
    font-weight: 700;
    color: white;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    letter-spacing: 1px;
    transition: all 0.3s ease;
}

.logo h1:hover {
    transform: scale(1.05);
    text-shadow: 0 3px 6px rgba(0, 0, 0, 0.4);
}

.footer{
    background: linear-gradient(135deg, #D8D0F0 0%, #E8E0F5 50%, #F0E8FA 100%);
    /* border-top: 1px solid rgba(124, 58, 237, 0.15); */
    padding: 20px 0;
    display: flex;
    justify-content: center;
    align-items: center;
    box-shadow: 0 -2px 8px rgba(124, 58, 237, 0.05);
}

.footer-content {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: #666;
}

.copyright {
    color: #7C3AED;
    font-weight: 500;
}

.separator {
    color: #7C3AED;
    font-weight: bold;
    opacity: 0.6;
}

.footer-link {
    color: #7C3AED;
    text-decoration: none;
    font-weight: 600;
    transition: all 0.3s ease;
    padding: 2px 4px;
    border-radius: 4px;
}

.footer-link:hover {
    color: #5B21B6;
    background-color: rgba(124, 58, 237, 0.1);
    text-decoration: none;
}

:deep(.el-menu){
    border-right: 0;
    background: none;
}

:deep(.el-avatar){
    --el-avatar-bg-color: transparent;
}
:deep(.el-header){
    position: sticky;
    z-index:99;
    top: 0; /* 或者其他你希望的顶部偏移量 */
}

:deep(.menus li){
    margin: 5px 8px 5px 8px;
    border-radius: 8px;
}
:deep(.menus li:hover){
    background-color: #DBCCFD;
    color:rgb(124, 58, 237);
}
:deep(.el-menu-item.is-active){
    color:rgb(124, 58, 237);
    background-color: #DBCCFD;
}

:deep(.el-header){
    padding:0;
}

:deep(.el-menu-item){
    height: 40px;
}

.user-info {
    padding: 16px;
    background-color: #f8f9fa;
    border-bottom: 1px solid #e4e7ed;
    margin-bottom: 4px;
}

.info-item {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
    font-size: 14px;
    color: #606266;
}

.info-item:last-child {
    margin-bottom: 0;
}

.info-item .el-icon {
    margin-right: 8px;
    color: #909399;
    font-size: 16px;
}

.info-item span {
    font-weight: 500;
}

/* 语言切换按钮样式 */
.language-switch {
    display: flex;
    align-items: center;
    margin-right: 16px;
    padding: 8px 12px;
    background: rgba(124, 58, 237, 0.1);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    border: 1px solid transparent;
}

.language-switch:hover {
    background: rgba(124, 58, 237, 0.15);
    border-color: rgba(124, 58, 237, 0.3);
    transform: translateY(-1px);
}

.language-icon {
    color: #7C3AED;
    flex-shrink: 0;
}

.language-text {
    margin-left: 6px;
    font-size: 14px;
    font-weight: 500;
    color: #7C3AED;
    line-height: 1;
}
</style>