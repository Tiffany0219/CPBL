<template>
  <div>
    <section class="section-header">
      <div>
        <p class="eyebrow">STANDINGS</p>
        <h2>球隊戰績</h2>
        <p>以球隊為主角整理排名、勝率、勝差、近況與團隊投打數據。</p>
      </div>
      <button class="btn-primary" :disabled="syncing" @click="syncStandings">
        <i :class="syncing ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-arrows-rotate'"></i>
        {{ syncing ? '更新中' : '更新戰績' }}
      </button>
    </section>

    <StateBox v-if="loading" type="loading" message="正在讀取戰績資料..." />
    <StateBox v-else-if="error" type="error" title="讀取失敗" :message="error" />

    <template v-else>
      <section v-if="teamCards.length" class="standings-team-grid">
        <article
          v-for="team in teamCards"
          :key="team.name"
          class="standings-team-card"
          :style="{ '--team-color': teamColor(team.name) }"
        >
          <div class="standings-team-rank">#{{ team.rank }}</div>
          <img :src="teamLogo(team.name)" :alt="team.name" />
          <div class="standings-team-main">
            <h3>{{ team.name }}</h3>
            <p>{{ team.record }} · 勝率 {{ team.winRate }}</p>
          </div>
          <div class="standings-team-stats">
            <span>勝差 <b>{{ team.gamesBehind }}</b></span>
            <span>近十 <b>{{ team.lastTen }}</b></span>
            <span>連續 <b>{{ team.streak }}</b></span>
          </div>
        </article>
      </section>

      <section class="tab-container">
        <div class="tab-slider" :style="{ transform: `translateX(${tabIndex * 100}%)` }"></div>
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :class="['tab-btn', { active: activeTab === tab.key }]"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </section>

      <section class="table-shell standings-table-shell">
        <StateBox
          v-if="currentRows.length === 0"
          title="尚未有戰績資料"
          message="請點擊更新戰績同步資料。"
        />
        <div v-else class="table-scroll">
          <table class="data-table standings-data-table">
            <thead>
              <tr>
                <th
                  v-for="header in headers"
                  :key="header"
                  :class="stickyClass(header)"
                >
                  {{ header }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in currentRows" :key="rowKey(row, index)">
                <td
                  v-for="header in headers"
                  :key="header"
                  :class="stickyClass(header)"
                >
                  <span v-if="header === '排名'" class="rank-badge">{{ rankOf(row, index) }}</span>
                  <span v-else-if="header === '球隊'" class="team-name">
                    <img :src="teamLogo(teamNameOf(row))" :alt="teamNameOf(row)" />
                    {{ teamNameOf(row) }}
                  </span>
                  <span v-else>{{ cellValue(row, header) }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, inject, onMounted, ref } from 'vue'
import { API_BASE, cpblApi } from '../api/cpblApi'
import StateBox from '../components/StateBox.vue'
import { TEAM_COLORS } from '../composables/usePlayerCollection'

const ASSET_BASE = API_BASE.replace(/\/api$/, '')
const notify = inject('notify', () => {})
const tabs = [
  { key: 'h2h', label: '對戰戰績' },
  { key: 'pitching', label: '團隊投球' },
  { key: 'batting', label: '團隊打擊' }
]

const teams = ['味全龍', '統一7-ELEVEn獅', '台鋼雄鷹', '富邦悍將', '樂天桃猿', '中信兄弟']
const teamLogoFiles = {
  中信兄弟: 'brothers.png',
  味全龍: 'dragons.png',
  樂天桃猿: 'monkeys.png',
  '統一7-ELEVEn獅': 'lions.png',
  富邦悍將: 'guardians.png',
  台鋼雄鷹: 'hawks.png'
}

const mainCols = ['出賽數', '勝-和-敗', '勝率', '勝差', '淘汰指數', '主場戰績', '客場戰績', '連勝/連敗', '近十場戰績']
const activeTab = ref('h2h')
const standings = ref({ h2h: [], pitching: [], batting: [] })
const loading = ref(false)
const syncing = ref(false)
const error = ref('')

const tabIndex = computed(() => tabs.findIndex(tab => tab.key === activeTab.value))
const currentRows = computed(() => standings.value?.[activeTab.value] || [])
const headers = computed(() => {
  if (activeTab.value === 'h2h') return ['排名', '球隊', ...mainCols, ...teams]
  const rowHeaders = currentRows.value.length ? Object.keys(currentRows.value[0]) : []
  return ['球隊', ...rowHeaders.filter(header => header !== '球隊')]
})

const teamCards = computed(() => {
  return (standings.value.h2h || []).map((row, index) => ({
    rank: rankOf(row, index),
    name: teamNameOf(row),
    record: row['勝-和-敗'] || '-',
    winRate: row['勝率'] || '-',
    gamesBehind: row['勝差'] || '-',
    streak: row['連勝/連敗'] || '-',
    lastTen: row['近十場戰績'] || '-'
  }))
})

function rankOf(row, index) {
  const rankTeam = row['排名球隊'] || ''
  return rankTeam.match(/^(\d+)/)?.[1] || index + 1
}

function teamNameOf(row) {
  const rankTeam = row['排名球隊'] || ''
  return rankTeam.replace(/^\d+/, '') || row['球隊'] || '-'
}

function cellValue(row, header) {
  if (activeTab.value === 'h2h' && teams.includes(header) && header === teamNameOf(row)) return '—'
  return row[header] ?? '-'
}

function rowKey(row, index) {
  return `${teamNameOf(row)}-${index}`
}

function stickyClass(header) {
  return {
    'sticky-rank-col': header === '排名',
    'sticky-team-col': header === '球隊',
    'sticky-team-col-no-rank': header === '球隊' && activeTab.value !== 'h2h'
  }
}

function teamLogo(team) {
  return `${ASSET_BASE}/static/image/teams/${teamLogoFiles[team] || 'default.png'}`
}

function teamColor(team) {
  return TEAM_COLORS[team] || '#334155'
}

async function loadStandings() {
  loading.value = true
  error.value = ''
  try {
    standings.value = await cpblApi.getStandings()
  } catch {
    error.value = '戰績資料讀取失敗，請確認 API 是否正常。'
  } finally {
    loading.value = false
  }
}

async function syncStandings() {
  syncing.value = true
  try {
    const result = await cpblApi.updateStandings()
    await loadStandings()
    if (result?.status === 'fallback') {
      notify({
        type: 'warning',
        title: '已保留本機戰績',
        message: result.message || '官方戰績頁暫時無法解析，已使用目前快取資料。'
      })
    } else {
      notify({ type: 'success', title: '戰績已更新', message: '球隊戰績資料同步完成。' })
    }
  } catch {
    notify({ type: 'error', title: '更新失敗', message: '請確認後端是否正常。' })
  } finally {
    syncing.value = false
  }
}

onMounted(loadStandings)
</script>
