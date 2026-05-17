<template>
  <nav class="sidebar">
    <h1 class="brand-logo">⚾GOBASE<span>!</span></h1>

    <ul class="nav-menu">
      <li v-for="item in menuItems" :key="item.key" :class="{ active: activePage === item.key }">
        <button type="button" @click="$emit('change-page', item.key)">
          <i :class="item.icon"></i>
          <span>{{ item.label }}</span>
          <i v-if="item.protected && !authUser" class="fa-solid fa-lock nav-lock"></i>
        </button>
      </li>
    </ul>

    <section class="sidebar-auth">
      <template v-if="authUser">
        <span>目前登入</span>
        <strong>{{ authUser.username }}</strong>
        <button type="button" :disabled="authLoading" @click="$emit('logout')">
          <i class="fa-solid fa-right-from-bracket"></i>
          登出
        </button>
      </template>

      <template v-else>
        <span>訪客模式</span>
        <p>瀏覽資料不用登入；抽卡、收藏與打線需使用卡牌帳號。</p>
        <input v-model="username" type="text" placeholder="帳號" autocomplete="username" />
        <input v-model="password" type="password" placeholder="密碼" autocomplete="current-password" @keyup.enter="submitLogin" />
        <div class="sidebar-auth-actions">
          <button type="button" :disabled="authLoading" @click="submitLogin">登入</button>
          <button type="button" :disabled="authLoading" @click="submitRegister">註冊</button>
        </div>
      </template>
    </section>
  </nav>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  activePage: {
    type: String,
    required: true
  },
  authUser: {
    type: Object,
    default: null
  },
  authLoading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['change-page', 'login', 'register', 'logout'])

const username = ref('')
const password = ref('')

function credentials() {
  return {
    username: username.value.trim(),
    password: password.value
  }
}

function submitLogin() {
  emit('login', credentials())
}

function submitRegister() {
  emit('register', credentials())
}

const menuItems = [
  { key: 'home', label: '首頁看板', icon: 'fa-solid fa-house' },
  { key: 'news', label: '最新消息', icon: 'fa-solid fa-newspaper' },
  { key: 'schedule', label: '賽程查詢', icon: 'fa-solid fa-calendar' },
  { key: 'broadcast', label: '文字轉播', icon: 'fa-solid fa-radio' },
  { key: 'standings', label: '球隊戰績', icon: 'fa-solid fa-ranking-star' },
  { key: 'stats', label: '數據統計', icon: 'fa-solid fa-chart-line' },
  { key: 'profile', label: '會員主頁', icon: 'fa-solid fa-user', protected: true },
  { key: 'gacha', label: '球員抽卡', icon: 'fa-solid fa-box-open', protected: true },
  { key: 'collection', label: '球員收藏', icon: 'fa-solid fa-layer-group', protected: true },
  { key: 'timeline', label: '看球足跡', icon: 'fa-solid fa-timeline', protected: true },
  { key: 'lineup', label: '我的打線', icon: 'fa-solid fa-users-rectangle', protected: true },
  { key: 'sync', label: '同步中心', icon: 'fa-solid fa-arrows-rotate' }
]
</script>
