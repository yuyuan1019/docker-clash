<template>
    <div class="notice">
        <slot></slot>
    </div>
</template>

<script setup>

</script>

<style>
.notice{
    border-left: 5px solid #409eff;
    padding: 8px 16px;
    background-color: #ECF5FF;
    border-radius: 5px;
    font-size:14px;
    color:#606266;
}

.notice a{
    text-decoration: none;
    color: #ff4d4d;
}

.notice ul{
    line-height:22px;
}

code {
  background-color: #E4E7ED;
  padding: 2px 4px;
  border-radius: 3px;
  font-size: 0.9em;
  color: #333;
  white-space: pre-wrap;
}

</style>