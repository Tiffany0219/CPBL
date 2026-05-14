<template>
  <div class="app-shell">
    <Sidebar :active-page="activePage" @change-page="activePage = $event" />

    <main class="main-content">
      <div :class="['api-status-pill', apiStatus]">
        <span class="api-status-dot"></span>
        {{ apiStatusText }}
      </div>

      <HomeView v-if="activePage === 'home'" @open-game="openGameDetail" @change-page="activePage = $event" />
      <NewsView v-else-if="activePage === 'news'" />
      <ScheduleView v-else-if="activePage === 'schedule'" @open-game="openGameDetail" />
      <StandingsView v-else-if="activePage === 'standings'" />
      <StatsView v-else-if="activePage === 'stats'" />
      <SyncView v-else-if="activePage === 'sync'" />
      <GachaView v-else-if="activePage === 'gacha'" @change-page="activePage = $event" />
      <CollectionView v-else-if="activePage === 'collection'" />
      <TimelineView v-else-if="activePage === 'timeline'" />
      <LineupView v-else-if="activePage === 'lineup'" />
    </main>

    <GameDetailModal
      :show="modalVisible"
      :detail="selectedGameDetail"
      :loading="detailLoading"
      :error="detailError"
      @close="closeGameDetail"
    />

    <div class="toast-stack" aria-live="polite">
      <article v-for="toast in toasts" :key="toast.id" :class="['toast-item', toast.type]">
        <i :class="toast.icon"></i>
        <div>
          <strong>{{ toast.title }}</strong>
          <p>{{ toast.message }}</p>
        </div>
        <button type="button" aria-label="關閉通知" @click="dismissToast(toast.id)">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </article>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, provide, ref } from 'vue'
import { cpblApi } from './api/cpblApi'
import Sidebar from './components/Sidebar.vue'
import GameDetailModal from './components/GameDetailModal.vue'
import HomeView from './views/HomeView.vue'
import NewsView from './views/NewsView.vue'
import ScheduleView from './views/ScheduleView.vue'
import StandingsView from './views/StandingsView.vue'
import StatsView from './views/StatsView.vue'
import SyncView from './views/SyncView.vue'
import GachaView from './views/GachaView.vue'
import CollectionView from './views/CollectionView.vue'
import TimelineView from './views/TimelineView.vue'
import LineupView from './views/LineupView.vue'

const activePage = ref('home')
const modalVisible = ref(false)
const selectedGameDetail = ref(null)
const detailLoading = ref(false)
const detailError = ref('')
const apiStatus = ref('checking')
const toasts = ref([])
let healthTimer = null

const toastIcons = {
  success: 'fa-solid fa-circle-check',
  error: 'fa-solid fa-triangle-exclamation',
  warning: 'fa-solid fa-circle-exclamation',
  info: 'fa-solid fa-circle-info'
}

const apiStatusText = computed(() => {
  if (apiStatus.value === 'ok') return 'API 已連線'
  if (apiStatus.value === 'error') return 'API 未連線'
  return '檢查 API'
})

function notify(payload) {
  const type = payload?.type || 'info'
  const toast = {
    id: `${Date.now()}-${Math.random()}`,
    type,
    icon: toastIcons[type] || toastIcons.info,
    title: payload?.title || (type === 'success' ? '完成' : type === 'error' ? '發生錯誤' : '提醒'),
    message: payload?.message || ''
  }

  toasts.value = [toast, ...toasts.value].slice(0, 4)
  window.setTimeout(() => dismissToast(toast.id), payload?.duration || 3600)
}

function dismissToast(id) {
  toasts.value = toasts.value.filter(toast => toast.id !== id)
}

provide('notify', notify)

async function checkApiHealth(showToast = false) {
  apiStatus.value = apiStatus.value === 'ok' ? 'ok' : 'checking'
  try {
    await cpblApi.getHealth()
    apiStatus.value = 'ok'
    if (showToast) {
      notify({ type: 'success', title: 'API 已連線', message: '後端服務回應正常。' })
    }
  } catch {
    apiStatus.value = 'error'
    if (showToast) {
      notify({ type: 'error', title: 'API 未連線', message: '請確認 Flask 後端是否已啟動。' })
    }
  }
}

async function openGameDetail(gameId) {
  modalVisible.value = true
  selectedGameDetail.value = null
  detailError.value = ''
  detailLoading.value = true

  try {
    selectedGameDetail.value = await cpblApi.getGameDetail(gameId)
  } catch (err) {
    console.error(err)
    notify({ type: 'error', title: '讀取失敗', message: '無法取得比賽詳細資料，請確認後端是否正常。' })
    detailError.value = '無法取得比賽詳細資料，請確認後端 /api/game/detail 是否正常。'
  } finally {
    detailLoading.value = false
  }
}

function closeGameDetail() {
  modalVisible.value = false
  selectedGameDetail.value = null
  detailError.value = ''
}

onMounted(() => {
  checkApiHealth()
  healthTimer = window.setInterval(checkApiHealth, 30000)
})

onUnmounted(() => {
  if (healthTimer) window.clearInterval(healthTimer)
})
</script>
