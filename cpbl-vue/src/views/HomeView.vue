<template>
  <div class="home-page">
    <section class="site-hero home-hero">
      <div class="home-hero-copy">
        <p class="eyebrow">CPBL SCOREBOARD</p>
        <h2>{{ homeDate }} {{ weekday }} 賽事看板</h2>
        <p class="hero-desc">
          今日賽事、即時狀態、收藏票夾與比賽詳情集中在同一個看板。
        </p>
        <div class="home-hero-actions">
          <button type="button" @click="$emit('change-page', 'schedule')">
            <i class="fa-solid fa-calendar-days"></i>
            月曆賽程
          </button>
          <button type="button" @click="$emit('change-page', 'stats')">
            <i class="fa-solid fa-ranking-star"></i>
            單項排行
          </button>
          <button type="button" @click="$emit('change-page', 'sync')">
            <i class="fa-solid fa-arrows-rotate"></i>
            同步中心
          </button>
        </div>
      </div>

      <div class="home-scoreboard">
        <span>GAMES</span>
        <strong>{{ games.length }}</strong>
        <small>{{ liveCount > 0 ? `${liveCount} 場 LIVE` : '目前沒有 LIVE 比賽' }}</small>
      </div>
    </section>

    <section class="home-summary-grid">
      <article v-for="item in summaryCards" :key="item.label" class="home-summary-card">
        <div :class="['home-summary-icon', item.tone]">
          <i :class="item.icon"></i>
        </div>
        <div>
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </div>
      </article>
    </section>

    <section class="toolbar-card home-toolbar">
      <div class="toolbar-title">
        <i class="fa-solid fa-baseball"></i>
        <span>賽事列表</span>
      </div>

      <div class="toolbar-actions">
        <button class="btn-soft" @click="shiftDate(-1)">
          <i class="fa-solid fa-chevron-left"></i>
          前一天
        </button>

        <button class="btn-soft" @click="shiftDate(1)">
          後一天
          <i class="fa-solid fa-chevron-right"></i>
        </button>

        <button class="btn-primary" :disabled="syncing" @click="syncToday">
          <i :class="syncing ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-rotate'"></i>
          {{ syncing ? '同步中' : '更新今日狀態' }}
        </button>
      </div>
    </section>

    <section class="game-list">
      <StateBox
        v-if="loading"
        type="loading"
        message="正在讀取今日賽事..."
      />

      <StateBox
        v-else-if="error"
        type="error"
        title="讀取失敗"
        :message="error"
      />

      <StateBox
        v-else-if="games.length === 0"
        :title="`${homeDate} 尚無比賽`"
        message="目前沒有賽程資料，可能是休賽日或尚未同步資料。"
      />

      <GameCard
        v-for="game in games"
        v-else
        :key="game.id"
        :game="game"
        :icon-only="true"
        :favorited="isFavorite(game.id)"
        :has-ticket="hasTicket(game.id)"
        :ticket-count="getTicketCount(game.id)"
        @open-detail="$emit('open-game', $event)"
        @toggle-favorite="toggleFavorite"
        @open-ticket="openTicketModal"
        @open-highlight="openHighlight"
      />
    </section>

    <TicketModal
      :show="showTicketModal"
      :game="selectedTicketGame"
      :tickets="selectedTicketGame ? getTickets(selectedTicketGame.id) : []"
      @close="closeTicketModal"
      @save="handleSaveTicket"
      @remove="handleRemoveTicket"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { cpblApi } from '../api/cpblApi'
import { getTodayMMDD, getWeekdayStr } from '../utils'

import StateBox from '../components/StateBox.vue'
import GameCard from '../components/GameCard.vue'
import TicketModal from '../components/TicketModal.vue'

import { useGameMemory } from '../composables/useGameMemory'

defineEmits(['open-game', 'change-page'])

const homeDate = ref(getTodayMMDD())
const games = ref([])
const loading = ref(false)
const syncing = ref(false)
const error = ref('')

const showTicketModal = ref(false)
const selectedTicketGame = ref(null)

const {
  isFavorite,
  toggleFavorite,
  hasTicket,
  getTickets,
  getTicketCount,
  addTicket,
  removeTicket
} = useGameMemory()

const weekday = computed(() => getWeekdayStr(homeDate.value))
const liveCount = computed(() => games.value.filter(game => game.status === 'LIVE').length)
const finishedCount = computed(() => games.value.filter(game => game.status === 'FINISH').length)
const postponedCount = computed(() => games.value.filter(game => game.status === '延賽' || game.status === 'POSTPONED').length)
const upcomingCount = computed(() => games.value.filter(game => !['LIVE', 'FINISH', '延賽', 'POSTPONED'].includes(game.status)).length)
const favoriteCount = computed(() => games.value.filter(game => isFavorite(game.id)).length)
const ticketedCount = computed(() => games.value.filter(game => hasTicket(game.id)).length)
const summaryCards = computed(() => [
  { label: '今日賽事', value: games.value.length, icon: 'fa-solid fa-calendar-day', tone: 'navy' },
  { label: 'LIVE', value: liveCount.value, icon: 'fa-solid fa-circle-play', tone: 'red' },
  { label: '已結束', value: finishedCount.value, icon: 'fa-solid fa-flag-checkered', tone: 'green' },
  { label: '未開賽', value: upcomingCount.value, icon: 'fa-solid fa-clock', tone: 'blue' },
  { label: '收藏', value: favoriteCount.value, icon: 'fa-solid fa-heart', tone: 'pink' },
  { label: '票夾', value: ticketedCount.value, icon: 'fa-solid fa-ticket', tone: 'gold' },
  { label: '延賽', value: postponedCount.value, icon: 'fa-solid fa-cloud-rain', tone: 'gray' }
])

async function loadGames() {
  loading.value = true
  error.value = ''

  try {
    games.value = await cpblApi.getGames({ date: homeDate.value })
  } catch (err) {
    console.error(err)
    error.value = '資料載入失敗，請確認 Flask 後端是否啟動。'
  } finally {
    loading.value = false
  }
}

function shiftDate(delta) {
  const [m, d] = homeDate.value.split('/')
  const date = new Date(2026, Number(m) - 1, Number(d))

  date.setDate(date.getDate() + delta)

  homeDate.value = `${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')}`

  loadGames()
}

async function syncToday() {
  syncing.value = true

  try {
    await cpblApi.updateToday()
    await loadGames()
    alert('✅ 同步完成')
  } catch (err) {
    console.error(err)
    alert('同步失敗，請確認 Flask 後端或爬蟲是否正常。')
  } finally {
    syncing.value = false
  }
}

function openTicketModal(game) {
  selectedTicketGame.value = game
  showTicketModal.value = true
}

function closeTicketModal() {
  showTicketModal.value = false
  selectedTicketGame.value = null
}

function handleSaveTicket(payload) {
  if (!selectedTicketGame.value) return

  addTicket(selectedTicketGame.value, payload)
  alert('已新增到觀賽票夾 🎟')
}

function handleRemoveTicket(ticketId) {
  if (!selectedTicketGame.value) return

  const confirmed = confirm('確定要刪除這筆觀賽紀錄嗎？')
  if (!confirmed) return

  removeTicket(selectedTicketGame.value.id, ticketId)
  alert('已刪除這筆觀賽紀錄')
}

function openHighlight(game) {
  const keyword = `${game.away} ${game.home} CPBL 精華`
  const url = `https://www.youtube.com/results?search_query=${encodeURIComponent(keyword)}`
  window.open(url, '_blank')
}

onMounted(loadGames)
</script>
