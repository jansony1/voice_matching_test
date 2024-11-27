import { createApp } from 'vue'
import './style.css'
import App from './App.vue'

// Polyfills
import { Buffer } from 'buffer'
window.Buffer = Buffer
window.process = {
  env: {},
  nextTick: function (callback) {
    setTimeout(callback, 0)
  }
}

createApp(App).mount('#app')
