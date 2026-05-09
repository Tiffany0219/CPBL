<template>
  <div>
    <section class="section-header">
      <div>
        <p class="eyebrow">ANALYTICS</p>
        <h2>數據統計</h2>
        <p>串接 CPBL 官方單項排行榜，快速查看投打榜首與前五名。</p>
      </div>

      <button class="btn-primary" type="button" :disabled="loading" @click="loadStats">
        <i :class="loading ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-rotate'"></i>
        {{ loading ? '更新中' : '更新排行榜' }}
      </button>
    </section>

    <section class="stats-grid stat-summary-grid">
      <article v-for="card in summaryCards" :key="card.label" class="stat-card">
        <div class="stat-icon"><i :class="card.icon"></i></div>
        <div>
          <p>{{ card.label }}</p>
          <strong>{{ card.value }}</strong>
        </div>
      </article>
    </section>

    <section class="stats-toolbar">
      <div class="view-toggle stats-filter-toggle">
        <button :class="{ active: filter === 'all' }" @click="filter = 'all'">全部</button>
        <button :class="{ active: filter === 'pitching' }" @click="filter = 'pitching'">投手</button>
        <button :class="{ active: filter === 'batting' }" @click="filter = 'batting'">打者</button>
      </div>

      <a class="stats-source-link" href="https://www.cpbl.com.tw/stats/toplist" target="_blank" rel="noreferrer">
        <i class="fa-solid fa-arrow-up-right-from-square"></i>
        CPBL 官方排行榜
      </a>
    </section>

    <StateBox v-if="loading" type="loading" message="正在讀取 CPBL 單項排行榜..." />
    <StateBox v-else-if="error" type="error" title="排行榜讀取失敗" :message="error" />

    <section v-else class="leaderboard-grid">
      <StateBox
        v-if="filteredCards.length === 0"
        title="暫無排行榜資料"
        message="請確認 Flask 後端是否啟動，或稍後重新整理。"
      />

      <article
        v-for="card in filteredCards"
        v-else
        :key="`${card.title}-${card.abbr}`"
        class="leaderboard-card"
      >
        <div class="leaderboard-head">
          <div>
            <h3>{{ card.title }}</h3>
            <span>{{ card.abbr }}</span>
          </div>
          <a :href="card.more_url" target="_blank" rel="noreferrer">
            更多資訊
            <i class="fa-solid fa-chevron-right"></i>
          </a>
        </div>

        <div class="leaderboard-body">
          <div class="leaderboard-photo">
            <img
              v-if="card.photo && !failedPhotos[card.title]"
              :src="card.photo"
              :alt="topLeader(card)?.name || card.title"
              @error="markPhotoFailed(card.title)"
            />
            <span v-else>{{ initials(topLeader(card)?.name) }}</span>
          </div>

          <ol class="leaderboard-list">
            <li v-for="leader in card.leaders" :key="`${card.title}-${leader.rank}-${leader.name}`">
              <span class="leader-rank">{{ leader.rank }}</span>
              <a class="leader-name" :href="leader.url" target="_blank" rel="noreferrer">
                {{ leader.name }}
                <small>{{ leader.team }}</small>
              </a>
              <b>{{ leader.value }}</b>
            </li>
          </ol>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { cpblApi } from '../api/cpblApi'
import StateBox from '../components/StateBox.vue'

const pitchingStats = ['ERA', 'W', 'SO', 'SV', 'HLD']
const battingStats = ['AVG', 'H', 'HR', 'RBI', 'SB']

const loading = ref(false)
const error = ref('')
const cards = ref([])
const games = ref([])
const filter = ref('all')
const failedPhotos = ref({})

const filteredCards = computed(() => {
  if (filter.value === 'pitching') return cards.value.filter(card => pitchingStats.includes(card.abbr))
  if (filter.value === 'batting') return cards.value.filter(card => battingStats.includes(card.abbr))
  return cards.value
})

const summaryCards = computed(() => {
  const finished = games.value.filter(game => game.status === 'FINISH').length
  const live = games.value.filter(game => game.status === 'LIVE').length
  const topEra = cards.value.find(card => card.abbr === 'ERA')?.leaders?.[0]
  const topAvg = cards.value.find(card => card.abbr === 'AVG')?.leaders?.[0]

  return [
    { label: '排行榜項目', value: cards.value.length || '-', icon: 'fa-solid fa-ranking-star' },
    { label: '已完成比賽', value: finished || '-', icon: 'fa-solid fa-flag-checkered' },
    { label: 'LIVE 比賽', value: live || '0', icon: 'fa-solid fa-circle-play' },
    { label: 'ERA 榜首', value: topEra ? topEra.name : '-', icon: 'fa-solid fa-baseball' },
    { label: 'AVG 榜首', value: topAvg ? topAvg.name : '-', icon: 'fa-solid fa-bullseye' },
    { label: '資料來源', value: 'CPBL', icon: 'fa-solid fa-database' }
  ]
})

function topLeader(card) {
  return card?.leaders?.[0] || null
}

function initials(name = '') {
  return (name || '球員').slice(0, 2)
}

function markPhotoFailed(title) {
  failedPhotos.value = {
    ...failedPhotos.value,
    [title]: true
  }
}

async function loadStats() {
  loading.value = true
  error.value = ''

  try {
    const [topStats, gameData] = await Promise.all([
      cpblApi.getTopStats({ limit: 10 }),
      cpblApi.getGames()
    ])

    cards.value = Array.isArray(topStats?.data) ? topStats.data : []
    games.value = Array.isArray(gameData) ? gameData : []
  } catch (err) {
    console.error(err)
    error.value = '排行榜資料讀取失敗，請確認 Flask 後端與 CPBL 官網是否正常。'
  } finally {
    loading.value = false
  }
}

onMounted(loadStats)
</script>
