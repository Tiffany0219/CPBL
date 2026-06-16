<template>
  <div>
    <section class="section-header">
      <div>
        <p class="eyebrow">FAN TIMELINE</p>
        <h2>我的看球足跡</h2>
        <p>把票夾裡的觀賽照片與心得整理成時間線，留下每一場比賽的記憶。</p>
      </div>

      <button class="btn-soft" type="button" @click="loadTimeline">
        <i class="fa-solid fa-rotate"></i>
        重新整理
      </button>
    </section>

    <section class="timeline-stats">
      <article class="lineup-summary-card">
        <span>觀賽紀錄</span>
        <strong>{{ timeline.length }}</strong>
      </article>
      <article class="lineup-summary-card">
        <span>造訪球場</span>
        <strong>{{ visitedLocations }}</strong>
      </article>
      <article class="lineup-summary-card">
        <span>最近一場</span>
        <strong>{{ latestDate }}</strong>
      </article>
    </section>

    <section class="timeline-filters">
      <div class="timeline-filter-buttons">
        <button
          v-for="option in timeFilters"
          :key="option.key"
          type="button"
          :class="{ active: selectedFilter === option.key }"
          @click="selectedFilter = option.key"
        >
          {{ option.label }}
        </button>
      </div>

      <div v-if="selectedFilter === 'custom'" class="timeline-date-range">
        <input v-model="customStart" type="date" aria-label="開始日期" />
        <span>到</span>
        <input v-model="customEnd" type="date" aria-label="結束日期" />
      </div>
    </section>

    <StateBox
      v-if="timeline.length === 0"
      :title="allTimeline.length === 0 ? '還沒有看球足跡' : '這段時間沒有紀錄'"
      :message="allTimeline.length === 0 ? '到首頁賽事卡片新增觀賽票夾，這裡就會自動長出你的球迷時間線。' : '換個時間段看看，或新增更多觀賽票夾。'"
    />

    <section v-else class="fan-timeline">
      <article v-for="ticket in timeline" :key="ticket.id" class="timeline-item">
        <div class="timeline-dot"></div>
        <div class="timeline-card">
          <div class="timeline-image">
            <img v-if="ticket.image" :src="ticket.image" alt="觀賽照片" />
            <div v-else>
              <i class="fa-regular fa-image"></i>
              <span>沒有照片</span>
            </div>
          </div>

          <div class="timeline-body">
            <span>{{ ticket.date || '未記錄日期' }} · {{ ticket.location || '未知球場' }}</span>
            <h3>{{ ticket.away }} vs {{ ticket.home }}</h3>
            <p>{{ ticket.note || '這場比賽還沒有心得。' }}</p>
            <small>{{ formatDate(ticket.createdAt) }}</small>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, inject, onMounted, ref } from 'vue'
import { cpblApi } from '../api/cpblApi'
import StateBox from '../components/StateBox.vue'
import { useGameMemory } from '../composables/useGameMemory'

const { getAllTickets } = useGameMemory()
const auth = inject('auth', null)
const allTimeline = ref([])
const selectedFilter = ref('all')
const customStart = ref('')
const customEnd = ref('')
const timeFilters = [
  { key: 'all', label: '全部' },
  { key: 'today', label: '今天' },
  { key: 'week', label: '近 7 天' },
  { key: 'month', label: '近 30 天' },
  { key: 'year', label: '今年' },
  { key: 'custom', label: '自訂' }
]

const timeline = computed(() => {
  const range = getFilterRange()
  return allTimeline.value.filter(ticket => {
    if (!range) return true
    const time = getTicketTimestamp(ticket)
    if (!time) return false
    return time >= range.start && time <= range.end
  })
})
const visitedLocations = computed(() => new Set(timeline.value.map(ticket => ticket.location).filter(Boolean)).size)
const latestDate = computed(() => timeline.value[0]?.date || '-')

async function loadTimeline() {
  try {
    if (auth?.token?.value) {
      allTimeline.value = await cpblApi.getUserTickets(auth.token.value)
      return
    }
  } catch {
    allTimeline.value = []
  }
  allTimeline.value = getAllTickets()
}

function getFilterRange() {
  const now = new Date()
  const today = startOfDay(now)
  const end = endOfDay(now)

  if (selectedFilter.value === 'today') {
    return { start: today.getTime(), end: end.getTime() }
  }
  if (selectedFilter.value === 'week') {
    const start = startOfDay(now)
    start.setDate(start.getDate() - 6)
    return { start: start.getTime(), end: end.getTime() }
  }
  if (selectedFilter.value === 'month') {
    const start = startOfDay(now)
    start.setDate(start.getDate() - 29)
    return { start: start.getTime(), end: end.getTime() }
  }
  if (selectedFilter.value === 'year') {
    const start = new Date(now.getFullYear(), 0, 1)
    const yearEnd = new Date(now.getFullYear(), 11, 31, 23, 59, 59, 999)
    return { start: start.getTime(), end: yearEnd.getTime() }
  }
  if (selectedFilter.value === 'custom') {
    const start = parseInputDate(customStart.value)
    const customRangeEnd = parseInputDate(customEnd.value, true)
    if (!start && !customRangeEnd) return null
    return {
      start: start ? start.getTime() : Number.NEGATIVE_INFINITY,
      end: customRangeEnd ? customRangeEnd.getTime() : Number.POSITIVE_INFINITY
    }
  }

  return null
}

function getTicketTimestamp(ticket) {
  const gameDate = parseGameDate(ticket.date)
  if (gameDate) return gameDate.getTime()
  const created = new Date(ticket.createdAt || '')
  return Number.isNaN(created.getTime()) ? 0 : startOfDay(created).getTime()
}

function parseGameDate(value) {
  if (!value) return null
  const text = String(value).trim()
  const full = text.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$/)
  const short = text.match(/^(\d{1,2})[-/](\d{1,2})$/)
  const year = new Date().getFullYear()
  const parts = full
    ? [Number(full[1]), Number(full[2]), Number(full[3])]
    : short
      ? [year, Number(short[1]), Number(short[2])]
      : null
  if (!parts) return null
  const date = new Date(parts[0], parts[1] - 1, parts[2])
  return Number.isNaN(date.getTime()) ? null : startOfDay(date)
}

function parseInputDate(value, useEndOfDay = false) {
  if (!value) return null
  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) return null
  return useEndOfDay ? endOfDay(date) : startOfDay(date)
}

function startOfDay(value) {
  const date = new Date(value)
  date.setHours(0, 0, 0, 0)
  return date
}

function endOfDay(value) {
  const date = new Date(value)
  date.setHours(23, 59, 59, 999)
  return date
}

function formatDate(value) {
  if (!value) return '未記錄建立時間'
  return new Date(value).toLocaleString('zh-TW', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  })
}

onMounted(loadTimeline)
</script>
