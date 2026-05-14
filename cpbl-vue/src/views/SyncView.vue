<template>
  <div>
    <section class="section-header">
      <div>
        <p class="eyebrow">SYNC CENTER</p>
        <h2>同步中心</h2>
        <p>集中管理賽程、戰績、新聞、排行榜與球員池資料。</p>
      </div>

      <button class="btn-primary" type="button" :disabled="checking" @click="checkHealth">
        <i :class="checking ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-stethoscope'"></i>
        {{ checking ? '檢查中' : '健康檢查' }}
      </button>
    </section>

    <section class="sync-health-grid">
      <article
        v-for="item in healthItems"
        :key="item.key"
        :class="['sync-health-card', item.status]"
      >
        <div class="sync-health-icon">
          <i :class="item.icon"></i>
        </div>
        <div>
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.message }}</small>
        </div>
      </article>
    </section>

    <section class="sync-layout">
      <div class="sync-actions-panel">
        <div class="lineup-panel-head">
          <div>
            <p class="eyebrow">DATA JOBS</p>
            <h3>資料任務</h3>
          </div>

          <label class="sync-month-picker">
            <span>月份</span>
            <select v-model="targetMonth">
              <option v-for="month in 12" :key="month" :value="month">{{ month }} 月</option>
            </select>
          </label>
        </div>

        <div class="sync-action-grid">
          <article v-for="action in actions" :key="action.key" class="sync-action-card">
            <div class="sync-action-icon">
              <i :class="action.icon"></i>
            </div>
            <div class="sync-action-copy">
              <h4>{{ action.title }}</h4>
              <p>{{ action.meta }}</p>
            </div>
            <button
              type="button"
              :disabled="!!runningKey"
              @click="runAction(action)"
            >
              <i :class="runningKey === action.key ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-play'"></i>
              {{ runningKey === action.key ? '執行中' : '執行' }}
            </button>
          </article>
        </div>
      </div>

      <div class="sync-log-panel">
        <div class="lineup-panel-head">
          <div>
            <p class="eyebrow">ACTIVITY</p>
            <h3>任務紀錄</h3>
          </div>
          <button class="btn-soft" type="button" :disabled="logs.length === 0" @click="logs = []">
            <i class="fa-solid fa-eraser"></i>
            清空
          </button>
        </div>

        <StateBox
          v-if="logs.length === 0"
          title="尚無任務紀錄"
          message="執行任務後，狀態與回傳摘要會顯示在這裡。"
        />

        <div v-else class="sync-log-list">
          <article v-for="log in logs" :key="log.id" :class="['sync-log-item', log.status]">
            <span>{{ log.time }}</span>
            <strong>{{ log.title }}</strong>
            <p>{{ log.message }}</p>
          </article>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { cpblApi } from '../api/cpblApi'
import { SEASON_YEAR } from '../utils'
import StateBox from '../components/StateBox.vue'

const currentMonth = new Date().getMonth() + 1
const targetMonth = ref(currentMonth)
const checking = ref(false)
const runningKey = ref('')
const logs = ref([])
const health = ref({
  games: { status: 'unknown', value: '-', message: '尚未檢查' },
  standings: { status: 'unknown', value: '-', message: '尚未檢查' },
  news: { status: 'unknown', value: '-', message: '尚未檢查' },
  topStats: { status: 'unknown', value: '-', message: '尚未檢查' },
  players: { status: 'unknown', value: '-', message: '尚未檢查' }
})

const healthItems = computed(() => [
  { key: 'games', label: '賽程 API', icon: 'fa-solid fa-calendar-days', ...health.value.games },
  { key: 'standings', label: '戰績資料', icon: 'fa-solid fa-ranking-star', ...health.value.standings },
  { key: 'news', label: '最新消息', icon: 'fa-solid fa-newspaper', ...health.value.news },
  { key: 'topStats', label: '單項排行', icon: 'fa-solid fa-chart-line', ...health.value.topStats },
  { key: 'players', label: '球員池', icon: 'fa-solid fa-users', ...health.value.players }
])

const actions = computed(() => [
  {
    key: 'today',
    title: '更新今日狀態',
    meta: '首頁賽事、比分、先發投手',
    icon: 'fa-solid fa-rotate',
    run: () => cpblApi.updateToday(),
    summarize: result => `更新完成，處理 ${result?.count ?? 0} 場`
  },
  {
    key: 'month',
    title: `同步 ${SEASON_YEAR} 年 ${targetMonth.value} 月賽程`,
    meta: '指定月份賽程、比分、延賽狀態',
    icon: 'fa-solid fa-calendar-check',
    run: () => cpblApi.updateMonth(targetMonth.value, SEASON_YEAR),
    summarize: result => `${result?.month ?? targetMonth.value} 月完成，處理 ${result?.count ?? 0} 場`
  },
  {
    key: 'gameExtras',
    title: `補抓 ${targetMonth.value} 月投手 / MVP`,
    meta: '只處理已完賽，寫入先發投手、勝敗投與官方 MVP',
    icon: 'fa-solid fa-baseball-bat-ball',
    run: () => cpblApi.updateGameExtras({ m: targetMonth.value, year: SEASON_YEAR, limit: 60 }),
    summarize: result => `補抓完成 ${result?.updated ?? 0} 場${result?.failed?.length ? `，失敗 ${result.failed.length} 場` : ''}`
  },
  {
    key: 'standings',
    title: '更新球隊戰績',
    meta: '對戰戰績、團隊投球、團隊打擊',
    icon: 'fa-solid fa-table-list',
    run: () => cpblApi.updateStandings(),
    summarize: result => `戰績更新完成，分類 ${Object.keys(result?.data || {}).length || 0} 組`
  },
  {
    key: 'news',
    title: '檢查最新消息',
    meta: 'CPBL 官方賽事新聞',
    icon: 'fa-solid fa-newspaper',
    run: () => cpblApi.getNews({ limit: 5 }),
    summarize: result => `讀取完成，取得 ${Array.isArray(result) ? result.length : 0} 則`
  },
  {
    key: 'topStats',
    title: '檢查單項排行榜',
    meta: '官方投打排行榜前五名',
    icon: 'fa-solid fa-ranking-star',
    run: () => cpblApi.getTopStats({ limit: 10 }),
    summarize: result => `讀取完成，取得 ${result?.data?.length ?? 0} 個排行榜`
  },
  {
    key: 'players',
    title: '初始化球員池',
    meta: '抽卡與收藏冊球員資料',
    icon: 'fa-solid fa-id-card',
    confirm: '初始化球員池可能需要比較久，確定要執行嗎？',
    run: () => cpblApi.initPlayerPool(),
    summarize: result => `球員池完成，目前 ${result?.total ?? 0} 位`
  }
])

function nowTime() {
  return new Date().toLocaleTimeString('zh-TW', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

function addLog(status, title, message) {
  logs.value = [
    {
      id: `${Date.now()}-${Math.random()}`,
      status,
      title,
      message,
      time: nowTime()
    },
    ...logs.value
  ].slice(0, 12)
}

function normalizeError(err) {
  return err?.message?.slice(0, 120) || '任務執行失敗'
}

async function runAction(action) {
  if (action.confirm && !confirm(action.confirm)) return

  runningKey.value = action.key
  addLog('running', action.title, '任務已開始')

  try {
    const result = await action.run()
    addLog('success', action.title, action.summarize(result))
    await checkHealth()
  } catch (err) {
    console.error(err)
    addLog('error', action.title, normalizeError(err))
  } finally {
    runningKey.value = ''
  }
}

async function checkHealth() {
  checking.value = true

  const checks = await Promise.allSettled([
    cpblApi.getHealth(),
    cpblApi.getGames(),
    cpblApi.getStandings(),
    cpblApi.getNews({ limit: 3 }),
    cpblApi.getTopStats({ limit: 3 }),
    cpblApi.getPlayerPool()
  ])

  const [api, games, standings, news, topStats, players] = checks

  health.value = {
    games: games.status === 'fulfilled'
      ? { status: api.status === 'fulfilled' ? 'ok' : 'warning', value: games.value.length, message: api.status === 'fulfilled' ? 'API 與賽程可讀取' : '賽程可讀取，健康檢查未回應' }
      : { status: 'error', value: '失敗', message: '賽程 API 異常' },
    standings: standings.status === 'fulfilled'
      ? { status: 'ok', value: standings.value?.h2h?.length || 0, message: '戰績可讀取' }
      : { status: 'error', value: '失敗', message: '戰績資料異常' },
    news: news.status === 'fulfilled'
      ? { status: 'ok', value: news.value.length, message: '新聞可讀取' }
      : { status: 'error', value: '失敗', message: '新聞 API 異常' },
    topStats: topStats.status === 'fulfilled'
      ? { status: 'ok', value: topStats.value?.data?.length || 0, message: '排行榜可讀取' }
      : { status: 'error', value: '失敗', message: '排行榜 API 異常' },
    players: players.status === 'fulfilled'
      ? { status: 'ok', value: players.value.length, message: '球員池可讀取' }
      : { status: 'warning', value: '未建立', message: '可初始化球員池' }
  }

  checking.value = false
}

onMounted(checkHealth)
</script>
