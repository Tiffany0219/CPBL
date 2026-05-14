<template>
  <div class="broadcast-page">
    <section class="section-header">
      <div>
        <p class="eyebrow">LIVE LOG</p>
        <h2>文字轉播</h2>
        <p>{{ selectedDate }} 的打席、跑壘與壘包狀態。</p>
      </div>

      <button class="btn-primary" type="button" :disabled="loading" @click="loadGames">
        <i :class="loading ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-rotate'"></i>
        {{ loading ? '讀取中' : '重新讀取' }}
      </button>
    </section>

    <section class="filter-bar">
      <div class="month-switcher broadcast-date-switcher">
        <button class="btn-soft" type="button" @click="shiftDate(-1)">
          <i class="fa-solid fa-chevron-left"></i>
        </button>
        <strong>{{ selectedDate }}</strong>
        <button class="btn-soft" type="button" @click="shiftDate(1)">
          <i class="fa-solid fa-chevron-right"></i>
        </button>
      </div>

      <button class="btn-soft today-btn" type="button" @click="goToday">
        <i class="fa-solid fa-location-crosshairs"></i>
        今天
      </button>
    </section>

    <section class="team-filter-strip schedule-team-strip">
      <button
        type="button"
        :class="{ active: selectedTeam === '' }"
        @click="selectTeam('')"
      >
        <i class="fa-solid fa-border-all"></i>
        全部
      </button>
      <button
        v-for="team in teams"
        :key="team"
        type="button"
        :class="{ active: selectedTeam === team }"
        @click="selectTeam(team)"
      >
        <img :src="teamLogo(team)" :alt="team" />
        {{ shortTeam(team) }}
      </button>
    </section>

    <section class="broadcast-summary-grid">
      <article class="home-summary-card">
        <div class="home-summary-icon navy">
          <i class="fa-solid fa-calendar-day"></i>
        </div>
        <div>
          <span>賽事</span>
          <strong>{{ games.length }}</strong>
        </div>
      </article>
      <article class="home-summary-card">
        <div class="home-summary-icon green">
          <i class="fa-solid fa-flag-checkered"></i>
        </div>
        <div>
          <span>可看轉播</span>
          <strong>{{ logReadyCount }}</strong>
        </div>
      </article>
      <article class="home-summary-card">
        <div class="home-summary-icon blue">
          <i class="fa-solid fa-baseball"></i>
        </div>
        <div>
          <span>狀態</span>
          <strong>{{ liveCount ? 'LIVE' : 'OK' }}</strong>
        </div>
      </article>
    </section>

    <section v-if="loading" class="game-list">
      <div v-for="i in 3" :key="`broadcast-skeleton-${i}`" class="ticket-skeleton">
        <div class="skeleton-line short"></div>
        <div class="skeleton-game-row">
          <div class="skeleton-team"></div>
          <div class="skeleton-score"></div>
          <div class="skeleton-team right"></div>
        </div>
        <div class="skeleton-line"></div>
      </div>
    </section>

    <StateBox
      v-else-if="error"
      type="error"
      title="讀取失敗"
      :message="error"
    />

    <StateBox
      v-else-if="games.length === 0"
      :title="`${selectedDate} 尚無比賽`"
      message="目前沒有這天的賽事資料。"
    />

    <section v-else class="game-list">
      <GameCard
        v-for="game in games"
        :key="game.id"
        :game="game"
        context="broadcast"
        :show-actions="false"
        @open-detail="$emit('open-game', $event)"
      />
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { API_BASE, cpblApi } from '../api/cpblApi'
import { SEASON_YEAR, getTodayMMDD } from '../utils'
import GameCard from '../components/GameCard.vue'
import StateBox from '../components/StateBox.vue'

defineEmits(['open-game'])

const ASSET_BASE = API_BASE.replace(/\/api$/, '')
const teams = ['中信兄弟', '味全龍', '樂天桃猿', '統一7-ELEVEn獅', '富邦悍將', '台鋼雄鷹']
const teamLogoFiles = {
  中信兄弟: 'brothers.png',
  味全龍: 'dragons.png',
  樂天桃猿: 'monkeys.png',
  '統一7-ELEVEn獅': 'lions.png',
  富邦悍將: 'guardians.png',
  台鋼雄鷹: 'hawks.png'
}

const selectedDate = ref(getTodayMMDD())
const selectedTeam = ref('')
const games = ref([])
const loading = ref(false)
const error = ref('')

const liveCount = computed(() => games.value.filter(game => game.status === 'LIVE').length)
const logReadyCount = computed(() => games.value.filter(game => game.status === 'FINISH' || game.status === 'LIVE').length)

function teamLogo(team) {
  return `${ASSET_BASE}/static/image/teams/${teamLogoFiles[team] || 'default.png'}`
}

function shortTeam(team) {
  return team.replace('7-ELEVEn', '7-11')
}

function selectTeam(team) {
  selectedTeam.value = team
  loadGames()
}

function shiftDate(delta) {
  const [m, d] = selectedDate.value.split('/')
  const date = new Date(SEASON_YEAR, Number(m) - 1, Number(d))
  date.setDate(date.getDate() + delta)
  selectedDate.value = `${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')}`
  loadGames()
}

function goToday() {
  selectedDate.value = getTodayMMDD()
  loadGames()
}

async function loadGames() {
  loading.value = true
  error.value = ''

  try {
    games.value = await cpblApi.getGames({
      date: selectedDate.value,
      team: selectedTeam.value
    })
  } catch (err) {
    console.error(err)
    error.value = '文字轉播賽事讀取失敗，請確認 Flask 後端是否啟動。'
  } finally {
    loading.value = false
  }
}

onMounted(loadGames)
</script>
