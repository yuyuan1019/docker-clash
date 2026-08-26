<template>
    <div class="migration">
        <Notice>
            <ul>
                <li>{{ $t('migration.notice1') }}</li>
                <li>{{ $t('migration.notice2') }}</li>
                <li>{{ $t('migration.notice3') }}</li>
            </ul>
        </Notice>

        <div class="upload-section">
            <div class="upload-card">
                <h3>{{ $t('data.import') }}</h3>
                <el-upload
                    ref="uploadRef"
                    class="upload-demo"
                    drag
                    :action="uploadUrl"
                    :headers="uploadHeaders"
                    :on-success="handleSuccess"
                    :on-error="handleError"
                    :on-change="handleFileChange"
                    :before-upload="beforeUpload"
                    :show-file-list="false"
                    :auto-upload="false"
                    name="file"
                    accept=".json"
                >
                    <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                    <div class="el-upload__text">
                        Drag a JSON file here, or <em>click to select</em>
                    </div>
                    <template #tip>
                        <div class="el-upload__tip">
                            {{ $t('migration.tips') }}
                        </div>
                    </template>
                </el-upload>

                <div class="file-info" v-if="selectedFile">
                    <el-alert
                        :title="`已选择文件: ${selectedFile.name}`"
                        type="success"
                        :closable="false"
                        show-icon>
                    </el-alert>
                </div>

                <div class="btns">
                    <el-button type="primary" @click="handleUpload" :disabled="!selectedFile">
                        {{ $t('start.import') }}
                    </el-button>
                    <el-button v-if="selectedFile" @click="clearFile">
                        {{ $t('reselect') }}
                    </el-button>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElLoading } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import req from '@/utils/req'
import Notice from '../notice.vue'
import { useI18n } from 'vue-i18n'

const { t, locale } = useI18n()

const uploadRef = ref()
const uploadUrl = '/api/import'
const uploadHeaders = ref({})
const selectedFile = ref(null)

// 文件选择变化处理
const handleFileChange = (file, fileList) => {
    selectedFile.value = file.raw
    // console.log('文件已选择:', file.name)
}

// 清除文件
const clearFile = () => {
    selectedFile.value = null
    uploadRef.value.clearFiles()
}

// 手动上传
const handleUpload = () => {
    if (!selectedFile.value) {
        ElMessage.warning(t('migration.warning'))
        return
    }
    
    // console.log('开始上传文件:', selectedFile.value.name)
    
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    
    const loading = ElLoading.service({
        lock: true,
        text: t('migration.loading'),
        background: 'rgba(0, 0, 0, 0.7)'
    })

    req.post(uploadUrl, formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    })
    .then(res => {
        if (res.data.code === 200) {
            ElMessage.success(res.data.msg || t('migration.success'))
            clearFile()
        } else {
            ElMessage.error(res.data.msg || t('migration.fail'))
        }
    })
    .catch(error => {
        // console.error('上传错误:', error)
        ElMessage.error(t('migration.upload.error'))
    })
    .finally(() => {
        loading.close()
    })
}

// 上传前验证
const beforeUpload = (file) => {
    const isJson = file.type === 'application/json' || file.name.endsWith('.json')
    const isLt10M = file.size / 1024 / 1024 < 10

    if (!isJson) {
        ElMessage.error(t('migration.only.json'))
        return false
    }
    if (!isLt10M) {
        ElMessage.error(t('migration.max.size'))
        return false
    }

    return false // 阻止自动上传
}

// 上传成功处理（备用）
const handleSuccess = (response, file) => {
    if (response.code === 200) {
        ElMessage.success(response.msg || t('migration.success'))
    } else {
        ElMessage.error(response.msg || t('migration.fail'))
    }
}

// 上传失败处理（备用）
const handleError = (error, file) => {
    // console.error('上传错误:', error)
    ElMessage.error(t('migration.upload.error'))
}
</script>

<style scoped>
.migration {
    /* padding: 20px; */
    width: 100%;
    margin: 0 auto;
}

.upload-section {
    margin-top: 2em;
    display: flex;
    justify-content: center;
}

.upload-card {
    background: #fff;
    border-radius: 8px;
    padding: 40px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    width: 100%;
    /* max-width: 800px; */
}

.upload-card h3 {
    margin-bottom: 2em;
    color: #303133;
    font-size: 20px;
    text-align: center;
    font-weight: 600;
}

.upload-demo {
    margin-bottom: 2em;
}

.file-info {
    margin: 1.5em 0;
}

.btns {
    text-align: center;
    margin-top: 2em;
}

.btns .el-button {
    margin: 0 10px;
    padding: 12px 30px;
    font-size: 14px;
}

:deep(.el-upload-dragger) {
    border: 2px dashed #d9d9d9;
    border-radius: 8px;
    width: 100%;
    height: 220px;
    text-align: center;
    cursor: pointer;
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: #fafafa;
}

:deep(.el-upload-dragger:hover) {
    border-color: #409eff;
    background: #f0f8ff;
}

:deep(.el-icon--upload) {
    font-size: 70px;
    color: #c0c4cc;
    margin-bottom: 20px;
    transition: color 0.3s ease;
}

:deep(.el-upload-dragger:hover .el-icon--upload) {
    color: #409eff;
}

:deep(.el-upload__text) {
    color: #606266;
    font-size: 16px;
    text-align: center;
    margin-bottom: 15px;
    line-height: 1.5;
}

:deep(.el-upload__text em) {
    color: #409eff;
    font-style: normal;
    font-weight: 600;
}

:deep(.el-upload__tip) {
    font-size: 13px;
    color: #909399;
    text-align: center;
    background: rgba(64, 158, 255, 0.1);
    padding: 8px 15px;
    border-radius: 4px;
    margin-top: 10px;
}

:deep(.el-alert) {
    border-radius: 6px;
}
</style>