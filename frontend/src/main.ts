import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import { router } from './app/router'
import { i18n, setLocale } from './i18n'
import './design-system/base.css'
import './design-system/components.css'
import './app/transitions.css'

setLocale('auto')
createApp(App).use(createPinia()).use(router).use(i18n).mount('#app')
