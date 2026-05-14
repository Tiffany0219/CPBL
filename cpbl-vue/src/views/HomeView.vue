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

    <section class="home-extras-grid">
      <article class="focus-player-card">
        <div>
          <p class="eyebrow">TODAY SPOTLIGHT</p>
          <h3>{{ featuredLeader.name }}</h3>
          <span>{{ featuredLeader.meta }}</span>
        </div>
        <strong>{{ featuredLeader.value }}</strong>
      </article>

      <article class="focus-player-card pitcher-card">
        <div>
          <p class="eyebrow">TODAY STARTER</p>
          <h3>{{ todayPitcher.name }}</h3>
          <span>{{ todayPitcher.meta }}</span>
        </div>
        <strong>{{ todayPitcher.badge }}</strong>
      </article>

      <article class="focus-player-card mvp-card">
        <div>
          <p class="eyebrow">TODAY MVP</p>
          <h3>{{ todayMvp.name }}</h3>
          <span>{{ todayMvp.meta }}</span>
        </div>
        <strong>{{ todayMvp.badge }}</strong>
      </article>

      <article class="baseball-tip-card">
        <i class="fa-solid fa-lightbulb"></i>
        <div>
          <p class="eyebrow">BASEBALL NOTE</p>
          <h3>{{ dailyTip.title }}</h3>
          <span>{{ dailyTip.text }}</span>
        </div>
      </article>
    </section>

    <section class="team-filter-strip">
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
      <template v-if="loading">
        <div v-for="i in 3" :key="`home-skeleton-${i}`" class="ticket-skeleton">
          <div class="skeleton-line short"></div>
          <div class="skeleton-game-row">
            <div class="skeleton-team"></div>
            <div class="skeleton-score"></div>
            <div class="skeleton-team right"></div>
          </div>
          <div class="skeleton-line"></div>
        </div>
      </template>

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
        :support-stats="getSupportStats(game.id)"
        :selected-support="getSupportChoice(game.id)"
        @open-detail="$emit('open-game', $event)"
        @toggle-favorite="toggleFavorite"
        @open-ticket="openTicketModal"
        @open-highlight="openHighlight"
        @support-team="supportTeam"
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
import { computed, inject, onMounted, ref } from 'vue'
import { API_BASE, cpblApi } from '../api/cpblApi'
import { SEASON_YEAR, getTodayMMDD, getWeekdayStr } from '../utils'

import StateBox from '../components/StateBox.vue'
import GameCard from '../components/GameCard.vue'
import TicketModal from '../components/TicketModal.vue'

import { useGameMemory } from '../composables/useGameMemory'

defineEmits(['open-game', 'change-page'])

const notify = inject('notify', () => {})
const ASSET_BASE = API_BASE.replace(/\/api$/, '')
const homeDate = ref(getTodayMMDD())
const games = ref([])
const topStats = ref([])
const selectedTeam = ref('')
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
  getSupportStats,
  getSupportChoice,
  addTicket,
  removeTicket,
  supportTeam
} = useGameMemory()

const teams = ['中信兄弟', '味全龍', '樂天桃猿', '統一7-ELEVEn獅', '富邦悍將', '台鋼雄鷹']
const teamLogoFiles = {
  中信兄弟: 'brothers.png',
  味全龍: 'dragons.png',
  樂天桃猿: 'monkeys.png',
  '統一7-ELEVEn獅': 'lions.png',
  富邦悍將: 'guardians.png',
  台鋼雄鷹: 'hawks.png'
}
const baseballTips = [
  { title: '雙殺守備', text: '一次守備讓兩名跑者出局，記錄常見為 DP。' },
  { title: '上壘率', text: 'OBP 衡量打者創造上壘機會，比打擊率更完整。' },
  { title: '救援成功', text: '投手在壓力局面守住領先，才會累積 SV。' },
  { title: '失誤上壘', text: '打者因守備失誤上壘時，會記為對方失誤，不列入安打。' },
  { title: '保送也是戰力', text: '選到四壞球能增加攻勢，也能消耗投手球數。' }
]

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
const featuredLeader = computed(() => {
  if (games.value.length > 0 && finishedCount.value === 0 && liveCount.value === 0) {
    return {
      name: selectedTeam.value || '賽前準備',
      meta: selectedTeam.value ? `${selectedTeam.value} 今日賽事尚未開打` : '今日賽事尚未開打',
      value: games.value.length ? `${games.value.length} 場` : '--'
    }
  }

  const preferredCards = topStats.value.filter(item => ['AVG', 'ERA', 'HR', 'RBI'].includes(item.abbr))
  const teamLeader = selectedTeam.value ? findLeaderForTeam(preferredCards, selectedTeam.value) : null
  const card = teamLeader?.card || preferredCards[0] || topStats.value[0]
  const leader = teamLeader?.leader || card?.leaders?.[0]

  if (selectedTeam.value && !teamLeader) {
    const teamMvpGame = games.value.find(game => sameTeam(game.mvp_team, selectedTeam.value) && game.mvp)
    if (teamMvpGame) {
      return {
        name: teamMvpGame.mvp,
        meta: `${selectedTeam.value} · 單場 MVP`,
        value: 'MVP'
      }
    }
  }

  if (!leader) {
    return {
      name: selectedTeam.value || 'GoBase Focus',
      meta: selectedTeam.value ? '目前篩選球隊' : '今日焦點球員待同步',
      value: games.value.length ? `${games.value.length} 場` : '--'
    }
  }

  return {
    name: leader.name,
    meta: `${leader.team || 'CPBL'} · ${card.title || card.abbr}`,
    value: leader.value
  }
})
const todayPitcher = computed(() => {
  if (games.value.length === 0) {
    return {
      name: '今日無比賽',
      meta: selectedTeam.value ? `${selectedTeam.value} 這天沒有賽程` : '休賽日或尚未同步賽程資料',
      badge: 'OFF'
    }
  }

  const candidates = games.value.flatMap(game => [
    {
      name: game.away_pitcher,
      team: game.away,
      opponent: game.home,
      gameTime: game.game_time,
      status: game.status
    },
    {
      name: game.home_pitcher,
      team: game.home,
      opponent: game.away,
      gameTime: game.game_time,
      status: game.status
    }
  ]).filter(item => item.name && item.name !== '-' && item.name !== '--')

  const pitcher = candidates.find(item => item.status === 'LIVE') || candidates[0]

  if (!pitcher) {
    return {
      name: '先發尚未公布',
      meta: selectedTeam.value ? `${selectedTeam.value} 今日先發尚未公布` : '賽前名單更新後會顯示先發投手',
      badge: 'SP'
    }
  }

  return {
    name: pitcher.name,
    meta: `${pitcher.team} vs ${pitcher.opponent} · ${pitcher.gameTime || '開賽時間待定'}`,
    badge: 'SP'
  }
})
const todayMvp = computed(() => {
  if (games.value.length > 0 && finishedCount.value === 0) {
    return {
      name: '賽後公布',
      meta: selectedTeam.value ? `${selectedTeam.value} 完賽後更新 MVP` : '今日比賽完賽後更新 MVP',
      badge: 'MVP'
    }
  }

  const battingCard = topStats.value.find(item => ['AVG', 'HR', 'RBI', 'H'].includes(item.abbr))
  const teamLeader = selectedTeam.value ? findLeaderForTeam([battingCard].filter(Boolean), selectedTeam.value) : null
  const finishedWithMvp = games.value.find(game => game.status === 'FINISH' && game.mvp)
  const selectedTeamGameMvp = selectedTeam.value
    ? games.value.find(game => game.status === 'FINISH' && game.mvp && isTeamGame(game, selectedTeam.value))
    : null

  if (selectedTeamGameMvp || (!selectedTeam.value && finishedWithMvp)) {
    const game = selectedTeamGameMvp || finishedWithMvp
    return {
      name: game.mvp,
      meta: selectedTeam.value
        ? `${game.mvp_team || 'CPBL'} · ${selectedTeam.value} 賽事 MVP`
        : `${game.mvp_team || 'CPBL'} · ${game.mvp_note || '官方 MVP'}`,
      badge: 'MVP'
    }
  }

  if (teamLeader?.leader) {
    return {
      name: teamLeader.leader.name,
      meta: `${teamLeader.leader.team || selectedTeam.value} · ${teamLeader.card.title || teamLeader.card.abbr} 隊內焦點 ${teamLeader.leader.value}`,
      badge: 'MVP'
    }
  }

  const leader = battingCard?.leaders?.[0]
  if (!selectedTeam.value && leader) {
    return {
      name: leader.name,
      meta: `${leader.team || 'CPBL'} · ${battingCard.title || battingCard.abbr} 榜首 ${leader.value}`,
      badge: 'MVP'
    }
  }

  const finished = games.value.find(game => game.status === 'FINISH')
  if (finished) {
    const awayScore = Number(finished.away_score)
    const homeScore = Number(finished.home_score)
    const winningTeam = awayScore > homeScore ? finished.away : homeScore > awayScore ? finished.home : '雙方'
    return {
      name: winningTeam,
      meta: `${finished.away} ${finished.away_score} : ${finished.home_score} ${finished.home}`,
      badge: 'WIN'
    }
  }

  return {
    name: selectedTeam.value ? `${selectedTeam.value} 焦點待同步` : 'MVP 待同步',
    meta: selectedTeam.value ? '該隊完賽或排行榜更新後會顯示球員' : '排行榜或完賽資料更新後會顯示今日 MVP 候選',
    badge: 'MVP'
  }
})
const dailyTip = computed(() => {
  const [, day = '1'] = homeDate.value.split('/')
  return baseballTips[(Number(day) - 1) % baseballTips.length]
})

function teamLogo(team) {
  return `${ASSET_BASE}/static/image/teams/${teamLogoFiles[team] || 'default.png'}`
}

function shortTeam(team) {
  return team.replace('7-ELEVEn', '7-11')
}

function sameTeam(a = '', b = '') {
  return a === b || shortTeam(a) === shortTeam(b)
}

function isTeamGame(game, team) {
  return sameTeam(game.away, team) || sameTeam(game.home, team)
}

function findLeaderForTeam(cards, team) {
  for (const card of cards) {
    const leader = card?.leaders?.find(item => sameTeam(item.team, team))
    if (leader) return { card, leader }
  }

  return null
}

function selectTeam(team) {
  selectedTeam.value = team
  loadGames()
}

async function loadGames() {
  loading.value = true
  error.value = ''

  try {
    const [gameResult, statsResult] = await Promise.allSettled([
      cpblApi.getGames({ date: homeDate.value, team: selectedTeam.value }),
      cpblApi.getTopStats({ limit: 6 })
    ])

    if (gameResult.status === 'rejected') throw gameResult.reason
    games.value = gameResult.value
    if (statsResult.status === 'fulfilled') {
      topStats.value = Array.isArray(statsResult.value?.data) ? statsResult.value.data : []
    }
  } catch (err) {
    console.error(err)
    error.value = '資料載入失敗，請確認 Flask 後端是否啟動。'
  } finally {
    loading.value = false
  }
}

function shiftDate(delta) {
  const [m, d] = homeDate.value.split('/')
  const date = new Date(SEASON_YEAR, Number(m) - 1, Number(d))

  date.setDate(date.getDate() + delta)

  homeDate.value = `${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')}`

  loadGames()
}

async function syncToday() {
  syncing.value = true

  try {
    await cpblApi.updateToday()
    await loadGames()
    notify({ type: 'success', title: '同步完成', message: '今日賽事狀態已更新。' })
  } catch (err) {
    console.error(err)
    notify({ type: 'error', title: '同步失敗', message: '請確認 Flask 後端或爬蟲是否正常。' })
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
  notify({ type: 'success', title: '已加入票夾', message: '觀賽紀錄已儲存。' })
}

function handleRemoveTicket(ticketId) {
  if (!selectedTicketGame.value) return

  const confirmed = confirm('確定要刪除這筆觀賽紀錄嗎？')
  if (!confirmed) return

  removeTicket(selectedTicketGame.value.id, ticketId)
  notify({ type: 'info', title: '已刪除', message: '這筆觀賽紀錄已移除。' })
}

function openHighlight(game) {
  const keyword = `${game.away} ${game.home} CPBL 精華`
  const url = `https://www.youtube.com/results?search_query=${encodeURIComponent(keyword)}`
  window.open(url, '_blank')
}

onMounted(loadGames)
</script>
