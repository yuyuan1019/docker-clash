<template>
    <div class="about">
        <div class="content">
            <div class="markdown-body" v-html="htmlContent"></div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import req from '@/utils/req'
import { marked } from 'marked'


// 自定义 renderer
const renderer = {
  // 自定义链接渲染方式
  link({href, title, text}) {
    return `<a href="${href}" title="${title || ''}" target="_blank">${text}</a>`;
  }
};

// 使用自定义的 renderer
marked.use({ renderer });

const htmlContent = ref('')

// 解析内容
const parseContent = () => {
    let content = `
## 关于Zurl
Zurl 是一款简单且实用的短链接系统，可以快速生成短链接，方便分享和管理。Zurl 旨在提供一个轻量级的解决方案，帮助用户更好地管理和跟踪链接。

### 功能特点

* **短链接生成**：用户可以将长链接转换为短链接，便于分享和传播。
* **链接管理**：提供直观的界面，管理员可以查看、编辑和删除。
* **延迟计数**：系统会延迟记录每个短链接的点击次数，避免高并发时压力过大。
* **自动获取标题**：添加链接时，系统会尝试自动获取长链接的标题，方便后续识别。
* **支持UA屏蔽**：管理员可以自定义需要屏蔽的User-Agent，防止恶意访问。
* **数据迁移**：支持将YOURLS数据迁移到Zurl，帮助用户过渡。
* **API**：提供API接口，方便二次开发和集成到任意系统。

### 技术栈

* 后端：Python3 + FastAPI
* 前端：Vue3 + Element Plus
* 数据库：SQLite
* 缓存：Redis


### 其他产品

如果您有兴趣，还可以了解我们的其他产品。

* [OneNav](https://www.onenav.top/) - 高效的浏览器书签管理工具，将您的书签集中式管理。
* [Zdir](https://www.zdir.pro/zh/) - 一款轻量级、多功能的文件分享程序。
* [ImgURL](https://www.imgurl.org/) - 2017年上线的免费图床。

### 技术支持

如果您需要付费技术支持，可通过以下方式与我们联系。

* 微信：xiaozme
* QQ：446199062

`;
    htmlContent.value = marked.parse(content);
}

onMounted(() => {
    parseContent()
})
</script>

<style scoped>
.products img{
    border-radius: 3px;
    width: auto;
    max-height: 130px;
    object-fit: cover;
}
.content{
    max-width: 800px;
    display: flex;
    justify-content: center;
}
.mardown-body{
    font-size:14px;
}
</style>