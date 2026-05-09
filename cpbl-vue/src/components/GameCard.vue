<template>
  <article class="ticket-card" @click="$emit('open-detail', game.id)">
    <div class="ticket-notch left"></div>
    <div class="ticket-notch right"></div>

    <div class="ticket-top">
      <div class="ticket-location">
        <i class="fa-solid fa-location-dot"></i>
        <span>{{ game.location || '未知球場' }}</span>
      </div>

      <div class="ticket-meta">
        <span class="ticket-date">{{ game.date }}</span>
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

    <div class="ticket-divider"></div>

    <div class="ticket-footer">
      <span>CPBL GAME TICKET</span>
      <span>點擊查看逐局比分與打擊數據</span>
    </div>

    <div class="game-actions" @click.stop>
      <button
        class="game-action-btn heart"
        :class="{ active: favorited }"
        @click="$emit('toggle-favorite', game)"
      >
        <i :class="favorited ? 'fa-solid fa-heart' : 'fa-regular fa-heart'"></i>
        {{ favorited ? '已收藏' : '收藏' }}
      </button>

      <button
        class="game-action-btn ticket"
        :class="{ active: hasTicket }"
        @click="$emit('open-ticket', game)"
      >
        <i class="fa-solid fa-ticket"></i>
        {{ hasTicket ? `票夾 ${ticketCount}` : '加入票夾' }}
      </button>

      <button
        class="game-action-btn video"
        @click="$emit('open-highlight', game)"
      >
        <i class="fa-solid fa-play"></i>
        精彩影片
      </button>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'

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
  }
})

defineEmits([
  'open-detail',
  'toggle-favorite',
  'open-ticket',
  'open-highlight'
])

const TEAM_LOGOS = {
  '中信兄弟': 'http://127.0.0.1:5000/static/image/teams/brothers.png',
  '味全龍': 'http://127.0.0.1:5000/static/image/teams/dragons.png',
  '樂天桃猿': 'http://127.0.0.1:5000/static/image/teams/monkeys.png',
  '統一7-ELEVEn獅': 'http://127.0.0.1:5000/static/image/teams/lions.png',
  '富邦悍將': 'http://127.0.0.1:5000/static/image/teams/guardians.png',
  '台鋼雄鷹': 'http://127.0.0.1:5000/static/image/teams/hawks.png'
}

function getTeamLogo(team) {
  return TEAM_LOGOS[team] || 'http://127.0.0.1:5000/static/image/teams/default.png'
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
</script>