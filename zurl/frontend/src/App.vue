<script setup>
import { RouterLink, RouterView } from 'vue-router'
import {ref,onMounted} from 'vue'
import { useRouter } from 'vue-router';
import req from '@/utils/req'
import { useSiteStore } from './stores/site';

const router = useRouter()
const siteStore = useSiteStore()

// 获取站点信息
const getSiteInfo = ()=>{
    req.get("/api/get/siteinfo")
    .then(res=>{
        if( res.data.code == 200 ) {
          if(res.data.data.is_init == "no") {
            router.push("/init")
          }
        }
    })
    .catch(err=>{
        console.log(err)
    })
}

onMounted(()=>{
    getSiteInfo()
})
</script>

<template>

  <RouterView />
</template>

<style>
body{
  margin:0;
  padding:0;
}
</style>
