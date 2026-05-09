<template>
  <div>
    <section class="site-hero">
      <div>
        <p class="eyebrow">CPBL SCOREBOARD</p>
        <h2>{{ homeDate }} {{ weekday }} 賽事看板</h2>
        <p class="hero-desc">
          查看指定日期的比賽組合、開打時間、比分狀態與比賽詳細資訊。
        </p>
      </div>
    </section>

    <section class="toolbar-card">
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
        @open-detail="openGameDetail"
        @toggle-favorite="toggleFavorite"
        @open-ticket="openTicketModal"
        @open-highlight="openHighlight"
      />
    </section>

    <GameDetailModal
      :show="showModal"
      :detail="selectedGameDetail"
      :loading="detailLoading"
      :error="detailError"
      @close="closeGameDetail"
    />

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
import GameDetailModal from '../components/GameDetailModal.vue'
import TicketModal from '../components/TicketModal.vue'

import { useGameMemory } from '../composables/useGameMemory'

const homeDate = ref(getTodayMMDD())
const games = ref([])
const loading = ref(false)
const syncing = ref(false)
const error = ref('')

const showModal = ref(false)
const selectedGameDetail = ref(null)
const detailLoading = ref(false)
const detailError = ref('')

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

async function openGameDetail(gameId) {
  showModal.value = true
  detailLoading.value = true
  detailError.value = ''
  selectedGameDetail.value = null

  try {
    selectedGameDetail.value = await cpblApi.getGameDetail(gameId)
  } catch (err) {
    console.error(err)
    detailError.value = '無法取得比賽詳細資料，請確認後端 /api/game/detail 是否正常。'
  } finally {
    detailLoading.value = false
  }
}

function closeGameDetail() {
  showModal.value = false
  selectedGameDetail.value = null
  detailError.value = ''
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