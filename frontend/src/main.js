import { createApp } from 'vue'

import App from './App.vue'
import './assets/base.css'
import router from './router/index.js'

createApp(App).use(router).mount('#app')

window.addEventListener('daily-fruit:auth-required', () => {
  router.replace({ name: 'login', query: { next: router.currentRoute.value.fullPath } })
})
