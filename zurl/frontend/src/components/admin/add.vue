<template>
    <div class="add">
        <el-form 
            label-position="top"
            :model="formData"
            ref="formRef"
            :rules="rules"
        >
            <el-form-item :label="$t('long.url')" prop="long_url">
                <el-input @blur="getLinkInfo(formData.long_url)" v-model="formData.long_url"></el-input>
            </el-form-item>

            <el-form-item :label="$t('custom.short.url')" prop="short_url">
                <el-input
                v-model="formData.short_url"
                placeholder="short_url"
                >
                <template #prepend>/</template>
                </el-input>
            </el-form-item>

            <el-form-item :label="$t('title')" prop="title">
                <el-input v-model="formData.title"></el-input>
            </el-form-item>

            <el-form-item :label="$t('validity.period.days')" v-if="props.utype === 'add'">
                <el-input v-model="formData.ttl_days" type="number" :placeholder="$t('validity.period.days.placeholder')"></el-input>
            </el-form-item>

            <el-form-item>
                <el-button v-if="props.utype === 'add'" type="primary" @click="addLink">{{ $t('add.link') }}</el-button>
                <el-button v-else-if="props.utype === 'edit'" type="primary" @click="updateLink">{{ $t('edit.link1') }}</el-button>
                <el-button @click="resetForm">{{ $t('reset') }}</el-button>
            </el-form-item>

        </el-form>
    </div>
</template>

<script setup>
import { ref,onMounted } from 'vue'
import req, { toForm } from '@/utils/req'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'

const { t, locale } = useI18n()

const props = defineProps(['url', 'utype'])

// 添加 emit 定义，完成事件
const emit = defineEmits(['finish'])

const formRef = ref(null)
const formData = ref({
    long_url: '',
    short_url: '',
    title: '',
    ttl_days: 0
})
const rules = {
    long_url: [
        { required: true, message: t('long.url.required'), trigger: 'blur' },
        { type: 'url', message: t('long.url.invalid'), trigger: 'blur' }
    ]}

// 添加链接函数
const addLink = () => {
    formRef.value.validate((valid) => {
        if (valid) {
            req.post("/api/shorten_url", formData.value)
            .then(res => {
                if (res.data.code === 200) {
                    ElMessage.success(t('link.add.success'))
                    // 触发 finish 事件，关闭弹窗
                    emit('finish')
                    // 重置表单
                    resetForm()
                } else {        
                    ElMessage.error(t(res.data.msg) || "Failed to add link")
                }
            })
            .catch(err => {
                console.error(err)
                ElMessage.error(t('link.add.error'))
            })
        } else {
            ElMessage.error(t('home.long_url.url'))
            formRef.value.clearValidate()
            formData.value = {
                long_url: '',
                short_url: '',
                title: ''
            }
        }
    })
}

// 更新链接函数
const updateLink = () => {
    formRef.value.validate((valid) => {
        if (valid) {
            let dataToUpdate = {
                description: "",
                long_url: formData.value.long_url,
                short_url: formData.value.short_url,
                title: formData.value.title
            }
            req.post("/api/update_url/" + formData.value.id, dataToUpdate)
            .then(res => {
                if (res.data.code === 200) {
                    ElMessage.success(t('link.update.success'))
                    emit('finish') // 触发 finish 事件，关闭弹窗
                    // 重置表单
                    resetForm()
                } else {
                    ElMessage.error(t(res.data.msg))
                }
            })
        } else {
            ElMessage.error(t('home.long_url.url'))
            formRef.value.clearValidate()
            formData.value = {
                long_url: '',
                short_url: '',
                title: ''
            }
        }
    })
}

// 重置表单
const resetForm = () => {
    formRef.value.resetFields()
    formData.value = {
        long_url: '',
        short_url: '',
        title: ''
    }
}

onMounted(() => {
    console.log(props.utype)
    if (props.url) {
        formData.value = props.url
    }
    else {
        resetForm()
    }
})

// 获取链接信息
const getLinkInfo = (url)=>{
    if (!url) {
        // ElMessage.warning("请输入长链接")
        return
    }
    req.post("/api/get_url_metadata", toForm({url:formData.value.long_url}))
    .then(res=>{
        if(res.data.code == 200){
            formData.value.title = res.data.data.title
            // formData.value.short_url = res.data.data.short_url
        }
        else{
            // ElMessage.error(res.data.msg)
        }
    })
    .catch(err=>{
        console.log(err)
        // ElMessage.error("获取链接信息失败")
    })
}
</script>

<style scoped>

</style>