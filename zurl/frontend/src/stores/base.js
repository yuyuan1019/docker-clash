import { defineStore } from "pinia";
// 引入el-message
import { ElMessage } from 'element-plus'

export const useBaseStore = defineStore('base',{
    state:()=>({

    }),
    actions:{
        // 实现一个复制文本的方法
        copyText(text) {
            let input = document.createElement("textarea");
            document.body.append(input)
            input.value = text
            input.select()
            document.execCommand("copy");
            input.remove();
            ElMessage.success('Copied');
        },


    }

})