<template>
  <article
    :class="['ticket-card', { 'icon-only': iconOnly }]"
    :style="teamAccentStyle"
    @click="$emit('open-detail', game.id)"
  >
    <div class="ticket-notch left"></div>
    <div class="ticket-notch right"></div>

    <div class="ticket-top">
      <div class="ticket-location">
        <i class="fa-solid fa-location-dot"></i>
        <span>{{ game.location || '未知球場' }}</span>
      </div>

      <div class="ticket-meta">
        <span class="ticket-date">{{ game.date }}</span>
        <span v-if="inningText" class="ticket-inning">{{ inningText }}</span>
        <span class="ticket-status" :class="statusClass">{{ statusText }}</span>
      </div>
    </div>

    <div class="ticket-main">
      <!-- 客隊 -->
      <div class="ticket-team">
        <img
          :src="getTeamLogo(game.away)"
          :alt="game.away"
          class="ticket-logo"
        />

        <div class="ticket-team-text">
          <small>AWAY</small>
          <strong>{{ game.away }}</strong>
        </div>
      </div>

      <!-- 比分 -->
      <div class="ticket-score">
        <span>{{ game.away_score ?? '-' }}</span>
        <em>VS</em>
        <span>{{ game.home_score ?? '-' }}</span>
      </div>

      <!-- 主隊 -->
      <div class="ticket-team right">
        <div class="ticket-team-text align-right">
          <small>HOME</small>
          <strong>{{ game.home }}</strong>
        </div>

        <img
          :src="getTeamLogo(game.home)"
          :alt="game.home"
          class="ticket-logo"
        />
      </div>
    </div>

    <div class="ticket-insights">
      <div class="ticket-insight">
        <span>
          <i class="fa-solid fa-baseball"></i>
          今日投手
        </span>
        <strong>{{ awayPitcher }}</strong>
        <small>{{ awayPitcherMeta }}</small>
      </div>

      <div class="ticket-insight center">
        <span>
          <i class="fa-solid fa-star"></i>
          今日 MVP
        </span>
        <strong>{{ mvpText }}</strong>
        <small>{{ mvpMeta }}</small>
      </div>

      <div class="ticket-insight right">
        <span>
          <i class="fa-solid fa-baseball"></i>
          今日投手
        </span>
        <strong>{{ homePitcher }}</strong>
        <small>{{ homePitcherMeta }}</small>
      </div>
    </div>

    <div class="ticket-divider"></div>

    <div class="ticket-footer">
      <span>{{ footerLabel }}</span>
      <span>{{ footerHint }}</span>
    </div>

    <div v-if="showActions" class="support-panel" @click.stop>
      <button
        type="button"
        :class="{ active: selectedSupport === 'away' }"
        @click="$emit('support-team', game, 'away')"
      >
        <span>{{ game.away }}</span>
        <strong>{{ awaySupportPercent }}%</strong>
      </button>
      <div class="support-meter" aria-hidden="true">
        <span :style="{ width: `${awaySupportPercent}%` }"></span>
      </div>
      <button
        type="button"
        :class="{ active: selectedSupport === 'home' }"
        @click="$emit('support-team', game, 'home')"
      >
        <span>{{ game.home }}</span>
        <strong>{{ homeSupportPercent }}%</strong>
      </button>
    </div>

    <div v-if="showActions" class="game-actions" @click.stop>
      <button
        class="game-action-btn heart"
        :class="{ active: favorited }"
        :title="favorited ? '已收藏' : '收藏'"
        :aria-label="favorited ? '已收藏' : '收藏'"
        @click="$emit('toggle-favorite', game)"
      >
        <i :class="favorited ? 'fa-solid fa-heart' : 'fa-regular fa-heart'"></i>
        <span class="action-label">{{ favorited ? '已收藏' : '收藏' }}</span>
      </button>

      <button
        class="game-action-btn ticket"
        :class="{ active: hasTicket }"
        :title="hasTicket ? `票夾 ${ticketCount}` : '加入票夾'"
        :aria-label="hasTicket ? `票夾 ${ticketCount}` : '加入票夾'"
        @click="$emit('open-ticket', game)"
      >
        <i class="fa-solid fa-ticket"></i>
        <span class="action-label">{{ hasTicket ? `票夾 ${ticketCount}` : '加入票夾' }}</span>
      </button>

      <button
        class="game-action-btn video"
        title="精彩影片"
        aria-label="精彩影片"
        @click="$emit('open-highlight', game)"
      >
        <i class="fa-solid fa-play"></i>
        <span class="action-label">精彩影片</span>
      </button>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { API_BASE } from '../api/cpblApi'
import { TEAM_COLORS } from '../composables/usePlayerCollection'

const props = defineProps({
  game: {
    type: Object,
    required: true
  },
  iconOnly: {
    type: Boolean,
    default: false
  },
  favorited: {
    type: Boolean,
    default: false
  },
  hasTicket: {
    type: Boolean,
    default: false
  },
  ticketCount: {
    type: Number,
    default: 0
  },
  showActions: {
    type: Boolean,
    default: true
  },
  context: {
    type: String,
    default: 'ticket'
  },
  supportStats: {
    type: Object,
    default: () => ({ away: 0, home: 0 })
  },
  selectedSupport: {
    type: String,
    default: ''
  }
})

defineEmits([
  'open-detail',
  'toggle-favorite',
  'open-ticket',
  'open-highlight',
  'support-team'
])

const ASSET_BASE = API_BASE.replace(/\/api$/, '')
const TEAM_LOGOS = {
  '中信兄弟': 'brothers.png',
  '味全龍': 'dragons.png',
  '樂天桃猿': 'monkeys.png',
  '統一7-ELEVEn獅': 'lions.png',
  '富邦悍將': 'guardians.png',
  '台鋼雄鷹': 'hawks.png'
}

const teamAccentStyle = computed(() => ({
  '--away-color': TEAM_COLORS[props.game.away] || '#1f5f99',
  '--home-color': TEAM_COLORS[props.game.home] || '#0f766e'
}))

function getTeamLogo(team) {
  const fileName = TEAM_LOGOS[team] || 'default.png'
  return `${ASSET_BASE}/static/image/teams/${fileName}`
}

const statusText = computed(() => {
  if (props.game.status === 'FINISH') return 'FINAL'
  if (props.game.status === 'LIVE') return 'LIVE'
  if (props.game.status === 'POSTPONED' || props.game.status === '延賽') return '延賽'
  return props.game.game_time || '未開賽'
})

const statusClass = computed(() => {
  if (props.game.status === 'FINISH') return 'final'
  if (props.game.status === 'LIVE') return 'live'
  if (props.game.status === 'POSTPONED' || props.game.status === '延賽') return 'postponed'
  return 'upcoming'
})

const inningText = computed(() => {
  if (props.game.status !== 'LIVE') return ''
  const value = cleanName(props.game.game_time)
  if (!value || value === 'LIVE') return ''
  return value.includes('局') ? `目前 ${value}` : value
})

function cleanName(value) {
  return value && value !== '-' && value !== '--' ? value : ''
}

function normalizeName(value) {
  if (cleanName(value)) return value
  return props.game.status === 'FINISH' ? '待同步' : '待公布'
}

function pitcherMeta(team, pitcher) {
  const name = cleanName(pitcher)
  const tags = [team]

  if (name && name === cleanName(props.game.winning_pitcher)) tags.push('勝投')
  if (name && name === cleanName(props.game.losing_pitcher)) tags.push('敗投')
  if (name && name === cleanName(props.game.save_pitcher)) tags.push('救援成功')

  return tags.join(' · ')
}

const awayPitcher = computed(() => normalizeName(props.game.away_pitcher))
const homePitcher = computed(() => normalizeName(props.game.home_pitcher))
const awayPitcherMeta = computed(() => pitcherMeta(props.game.away, props.game.away_pitcher))
const homePitcherMeta = computed(() => pitcherMeta(props.game.home, props.game.home_pitcher))
const mvpText = computed(() => {
  if (cleanName(props.game.mvp || props.game.mvp_name)) return props.game.mvp || props.game.mvp_name
  if (props.game.status === 'FINISH') return '待同步'
  if (props.game.status === 'LIVE') return '比賽中'
  return '待公布'
})
const mvpMeta = computed(() => {
  if (cleanName(props.game.mvp || props.game.mvp_name)) {
    if (props.game.mvp_note) return props.game.mvp_note
    if (props.game.mvp_team) return `${props.game.mvp_team} · 官方 MVP`
    return '官方 MVP'
  }
  if (props.game.status === 'FINISH') return '同步中心可補抓'
  if (props.game.status === 'LIVE') return '賽後更新'
  return '賽後公布'
})

const supportTotal = computed(() => Number(props.supportStats.away || 0) + Number(props.supportStats.home || 0))
const awaySupportPercent = computed(() => {
  if (!supportTotal.value) return 50
  return Math.round((Number(props.supportStats.away || 0) / supportTotal.value) * 100)
})
const homeSupportPercent = computed(() => 100 - awaySupportPercent.value)
const footerLabel = computed(() => (props.context === 'broadcast' ? 'LIVE LOG CENTER' : 'CPBL GAME TICKET'))
const footerHint = computed(() => (
  props.context === 'broadcast'
    ? '點擊查看文字轉播與壘包狀態'
    : '點擊查看逐局比分與打擊數據'
))
</script>
