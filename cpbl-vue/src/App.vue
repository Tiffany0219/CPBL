<template>
  <div class="app-shell">
    <Sidebar
      :active-page="activePage"
      :auth-user="authUser"
      :auth-loading="authLoading"
      @change-page="handlePageChange"
      @login="handleLogin"
      @register="handleRegister"
      @logout="handleLogout"
    />

    <main class="main-content">
      <div :class="['api-status-pill', apiStatus]">
        <span class="api-status-dot"></span>
        {{ apiStatusText }}
      </div>

      <HomeView v-if="activePage === 'home'" @open-game="openGameDetail" @change-page="activePage = $event" />
      <NewsView v-else-if="activePage === 'news'" />
      <ScheduleView v-else-if="activePage === 'schedule'" @open-game="openGameDetail" />
      <BroadcastView v-else-if="activePage === 'broadcast'" @open-game="openGameDetail" />
      <StandingsView v-else-if="activePage === 'standings'" />
      <StatsView v-else-if="activePage === 'stats'" />
      <SyncView v-else-if="activePage === 'sync'" />
      <section v-else-if="activePageNeedsAuth" class="auth-required-card">
        <div class="auth-required-icon">
          <i class="fa-solid fa-lock"></i>
        </div>
        <p class="eyebrow">MEMBER ONLY</p>
        <h2>{{ protectedPageTitle }}</h2>
        <p>訪客可以自由瀏覽賽程、戰績與文字轉播；要收集卡牌、查看收藏或編輯打線時，請先在左側登入或註冊。</p>
        <button class="btn-primary" type="button" @click="activePage = 'home'">
          <i class="fa-solid fa-house"></i>
          回首頁瀏覽
        </button>
      </section>
      <GachaView v-else-if="activePage === 'gacha'" @change-page="activePage = $event" />
      <CollectionView v-else-if="activePage === 'collection'" />
      <ProfileView v-else-if="activePage === 'profile'" />
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

    <AiAssistant :active-page="activePage" />

    <div v-if="confirmState.visible" class="modal confirm-modal-backdrop">
      <section class="confirm-modal">
        <div class="confirm-modal-icon">
          <i :class="confirmState.icon"></i>
        </div>
        <div>
          <p class="eyebrow">CONFIRM</p>
          <h3>{{ confirmState.title }}</h3>
          <p>{{ confirmState.message }}</p>
        </div>
        <div class="confirm-modal-actions">
          <button class="btn-soft" type="button" @click="resolveConfirm(false)">
            {{ confirmState.cancelText }}
          </button>
          <button :class="['btn-primary', { danger: confirmState.danger }]" type="button" @click="resolveConfirm(true)">
            {{ confirmState.confirmText }}
          </button>
        </div>
      </section>
    </div>

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
import { saveCollectionMap } from './composables/usePlayerCollection'
import Sidebar from './components/Sidebar.vue'
import GameDetailModal from './components/GameDetailModal.vue'
import AiAssistant from './components/AiAssistant.vue'
import HomeView from './views/HomeView.vue'
import NewsView from './views/NewsView.vue'
import ScheduleView from './views/ScheduleView.vue'
import BroadcastView from './views/BroadcastView.vue'
import StandingsView from './views/StandingsView.vue'
import StatsView from './views/StatsView.vue'
import SyncView from './views/SyncView.vue'
import GachaView from './views/GachaView.vue'
import CollectionView from './views/CollectionView.vue'
import ProfileView from './views/ProfileView.vue'
import TimelineView from './views/TimelineView.vue'
import LineupView from './views/LineupView.vue'

const activePage = ref('home')
const modalVisible = ref(false)
const selectedGameDetail = ref(null)
const detailLoading = ref(false)
const detailError = ref('')
const apiStatus = ref('checking')
const toasts = ref([])
const authUser = ref(null)
const authToken = ref(localStorage.getItem('cpbl_auth_token') || '')
const authLoading = ref(false)
const confirmState = ref({
  visible: false,
  title: '',
  message: '',
  confirmText: '確定',
  cancelText: '取消',
  icon: 'fa-solid fa-circle-question',
  danger: false,
  resolver: null
})
let healthTimer = null

const protectedPages = {
  profile: '會員主頁需要登入',
  gacha: '球員抽卡需要登入',
  collection: '球員收藏需要登入',
  timeline: '看球足跡需要登入',
  lineup: '我的打線需要登入'
}

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

const activePageNeedsAuth = computed(() => Boolean(protectedPages[activePage.value] && !authUser.value))
const protectedPageTitle = computed(() => protectedPages[activePage.value] || '這個功能需要登入')

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

function handlePageChange(page) {
  activePage.value = page
  if (protectedPages[page] && !authUser.value) {
    notify({ type: 'info', title: '訪客模式', message: '這個功能會保存個人資料，請先登入或註冊。' })
  }
}

provide('notify', notify)
provide('confirmAction', confirmAction)
provide('auth', {
  user: authUser,
  token: authToken,
  refreshCards: refreshAuthCards
})

function confirmAction(options = {}) {
  return new Promise(resolve => {
    confirmState.value = {
      visible: true,
      title: options.title || '確認操作',
      message: options.message || '確定要繼續嗎？',
      confirmText: options.confirmText || '確定',
      cancelText: options.cancelText || '取消',
      icon: options.icon || (options.danger ? 'fa-solid fa-triangle-exclamation' : 'fa-solid fa-circle-question'),
      danger: Boolean(options.danger),
      resolver: resolve
    }
  })
}

function resolveConfirm(value) {
  const resolver = confirmState.value.resolver
  confirmState.value = {
    visible: false,
    title: '',
    message: '',
    confirmText: '確定',
    cancelText: '取消',
    icon: 'fa-solid fa-circle-question',
    danger: false,
    resolver: null
  }
  resolver?.(value)
}

function collectionListToMap(cards = []) {
  return cards.reduce((map, card) => {
    map[card.name] = card
    return map
  }, {})
}

async function refreshAuthCards() {
  if (!authToken.value) return []
  const cards = await cpblApi.getUserCards(authToken.value)
  saveCollectionMap(collectionListToMap(cards))
  return cards
}

async function setAuthSession(result) {
  authUser.value = result.user
  authToken.value = result.token
  localStorage.setItem('cpbl_auth_token', result.token)
  await refreshAuthCards()
}

async function handleLogin(payload) {
  authLoading.value = true
  try {
    const result = await cpblApi.login(payload.username, payload.password)
    await setAuthSession(result)
    notify({ type: 'success', title: '登入成功', message: `${result.user.username} 的卡牌收藏已同步。` })
  } catch (err) {
    notify({ type: 'error', title: '登入失敗', message: normalizeApiError(err) })
  } finally {
    authLoading.value = false
  }
}

async function handleRegister(payload) {
  authLoading.value = true
  try {
    const result = await cpblApi.register(payload.username, payload.password)
    await setAuthSession(result)
    notify({ type: 'success', title: '註冊成功', message: `${result.user.username} 已建立，卡牌收藏會存到帳號。` })
  } catch (err) {
    notify({ type: 'error', title: '註冊失敗', message: normalizeApiError(err) })
  } finally {
    authLoading.value = false
  }
}

function handleLogout() {
  authUser.value = null
  authToken.value = ''
  localStorage.removeItem('cpbl_auth_token')
  saveCollectionMap({})
  notify({ type: 'info', title: '已登出', message: '目前是訪客模式，可瀏覽公開賽事資料。' })
}

function normalizeApiError(err) {
  try {
    const parsed = JSON.parse(err.message)
    return parsed.error || err.message
  } catch {
    return err?.message || '請稍後再試'
  }
}

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
    window.dispatchEvent(new CustomEvent('cpbl-game-detail-updated', {
      detail: {
        id: gameId,
        detail: selectedGameDetail.value
      }
    }))
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
  if (authToken.value) {
    cpblApi.getMe(authToken.value)
      .then(async result => {
        authUser.value = result.user
        await refreshAuthCards()
      })
      .catch(() => handleLogout())
  }
  healthTimer = window.setInterval(checkApiHealth, 30000)
})

onUnmounted(() => {
  if (healthTimer) window.clearInterval(healthTimer)
})
</script>
