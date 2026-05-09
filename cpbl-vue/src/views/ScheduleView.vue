<template>
  <div>
    <section class="section-header">
      <div>
        <p class="eyebrow">SCHEDULE</p>
        <h2>2026 一軍賽程</h2>
        <p>依月份與球隊快速查詢賽程，支援月曆與列表兩種檢視模式。</p>
      </div>
      <button class="btn-primary" :disabled="syncing" @click="syncMonth">
        <i :class="syncing ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-rotate'"></i>
        {{ syncing ? '同步中' : `同步 ${currentMonth} 月` }}
      </button>
    </section>

    <section class="filter-bar">
      <div class="filter-group">
        <label>球隊</label>
        <select v-model="selectedTeam" @change="loadSchedule">
          <option value="">所有球隊</option>
          <option v-for="team in teams" :key="team" :value="team">{{ team }}</option>
        </select>
      </div>

      <div class="month-switcher">
        <button class="btn-soft" @click="changeMonth(-1)">‹</button>
        <strong>{{ currentMonth }} 月</strong>
        <button class="btn-soft" @click="changeMonth(1)">›</button>
      </div>

      <div class="view-toggle">
        <button :class="{ active: viewMode === 'calendar' }" @click="viewMode = 'calendar'">月曆</button>
        <button :class="{ active: viewMode === 'list' }" @click="viewMode = 'list'">列表</button>
      </div>
    </section>

    <StateBox v-if="loading" type="loading" message="正在讀取賽程資料..." />
    <StateBox v-else-if="error" type="error" title="讀取失敗" :message="error" />

    <section v-else>
      <div v-if="viewMode === 'calendar'" class="calendar-grid">
        <div v-for="day in weekDays" :key="day" class="calendar-header">{{ day }}</div>
        <div v-for="i in firstDay" :key="`empty-${i}`" class="calendar-day empty"></div>
        <div
          v-for="day in daysInMonth"
          :key="day"
          :class="['calendar-day', { 'has-game': gamesByDate[dateString(day)]?.length }]"
          @click="showDayDetail(dateString(day))"
        >
          <div class="day-num">{{ day }}</div>
          <div class="game-previews">
            <div v-for="game in (gamesByDate[dateString(day)] || []).slice(0, 2)" :key="game.id" class="mini-game">
              {{ game.away }} vs {{ game.home }}
            </div>
            <div v-if="(gamesByDate[dateString(day)] || []).length > 2" class="mini-more">
              +{{ gamesByDate[dateString(day)].length - 2 }}
            </div>
          </div>
        </div>
      </div>

      <div v-else>
        <StateBox v-if="monthGames.length === 0" :title="`${currentMonth} 月查無賽程`" message="可以嘗試切換月份、球隊，或先執行同步資料。" />
        <div v-for="date in sortedDates" :key="date" class="schedule-group">
          <div class="schedule-date-title">
            <span>{{ date }}</span>
            <small>{{ getWeekdayStr(date) }}</small>
          </div>
          <div class="game-list">
            <GameCard v-for="game in groupedMonthGames[date]" :key="game.id" :game="game" @open="$emit('open-game', $event)" />
          </div>
        </div>
      </div>

      <section v-if="selectedDate" class="day-detail">
        <div class="schedule-date-title">
          <span>{{ selectedDate }}</span>
          <small>賽事詳情</small>
        </div>
        <div class="game-list">
          <GameCard v-for="game in dayGames" :key="game.id" :game="game" @open="$emit('open-game', $event)" />
        </div>
      </section>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { cpblApi } from '../api/cpblApi'
import { getWeekdayStr, groupBy } from '../utils'
import StateBox from '../components/StateBox.vue'
import GameCard from '../components/GameCard.vue'

defineEmits(['open-game'])

const teams = ['中信兄弟', '味全龍', '樂天桃猿', '統一7-ELEVEn獅', '富邦悍將', '台鋼雄鷹']
const weekDays = ['日', '一', '二', '三', '四', '五', '六']

const selectedTeam = ref('')
const currentMonth = ref(new Date().getMonth() + 1)
const viewMode = ref('calendar')
const games = ref([])
const selectedDate = ref('')
const loading = ref(false)
const syncing = ref(false)
const error = ref('')

const firstDay = computed(() => new Date(2026, currentMonth.value - 1, 1).getDay())
const daysInMonth = computed(() => new Date(2026, currentMonth.value, 0).getDate())
const monthGames = computed(() => games.value.filter(g => Number((g.date || '').split('/')[0]) === currentMonth.value))
const gamesByDate = computed(() => groupBy(games.value, g => g.date || '未定'))
const groupedMonthGames = computed(() => groupBy(monthGames.value, g => g.date || '未定'))
const sortedDates = computed(() => Object.keys(groupedMonthGames.value).sort())
const dayGames = computed(() => games.value.filter(g => g.date === selectedDate.value))

function dateString(day) {
  return `${String(currentMonth.value).padStart(2, '0')}/${String(day).padStart(2, '0')}`
}

async function loadSchedule() {
  loading.value = true
  error.value = ''
  selectedDate.value = ''
  try {
    games.value = await cpblApi.getGames({ team: selectedTeam.value })
  } catch {
    error.value = '賽程資料讀取失敗，請確認 Flask 是否啟動。'
  } finally {
    loading.value = false
  }
}

function changeMonth(delta) {
  currentMonth.value += delta
  if (currentMonth.value > 12) currentMonth.value = 1
  if (currentMonth.value < 1) currentMonth.value = 12
  selectedDate.value = ''
}

function showDayDetail(date) {
  selectedDate.value = date
}

async function syncMonth() {
  syncing.value = true
  try {
    await cpblApi.updateMonth(currentMonth.value)
    await loadSchedule()
    alert(`✅ ${currentMonth.value} 月同步完成`)
  } catch {
    alert('同步失敗，請確認後端或爬蟲是否正常。')
  } finally {
    syncing.value = false
  }
}

onMounted(loadSchedule)
</script>
