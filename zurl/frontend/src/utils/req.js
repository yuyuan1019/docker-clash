import axios from 'axios';

const req = axios.create({
  baseURL: import.meta.env.VITE_API_URL, // 对于 Vite
  // baseURL: process.env.VUE_APP_API_BASE_URL || '/', // 对于 Vue CLI
  timeout: 30000,
});


// 请求拦截器
req.interceptors.request.use(
  (config) => {
    // 从 localStorage 或 sessionStorage 中获取 token
    const token = localStorage.getItem('token');

    // 如果 token 存在，则将其添加到请求头中
    if (token) {
      config.headers['Authorization'] = "Bearer " + token; // 设置 X-Token 头
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export function toForm(data) {
  const formData = new FormData();
  for (const key in data) {
      if (data.hasOwnProperty(key)) {
          formData.append(key, data[key]);
      }
  }
  return formData;
}

export default req;