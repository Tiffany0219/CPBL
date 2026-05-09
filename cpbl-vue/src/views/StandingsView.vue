<template>
  <div>
    <section class="section-header">
      <div>
        <p class="eyebrow">STANDINGS</p>
        <h2>球隊戰績</h2>
        <p>查看球隊排名、對戰戰績、投球與打擊數據。</p>
      </div>
      <button class="btn-primary" :disabled="syncing" @click="syncStandings">
        <i :class="syncing ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-arrows-rotate'"></i>
        {{ syncing ? '更新中' : '更新戰績' }}
      </button>
    </section>

    <section class="tab-container">
      <div class="tab-slider" :style="{ transform: `translateX(${tabIndex * 100}%)` }"></div>
      <button v-for="tab in tabs" :key="tab.key" :class="['tab-btn', { active: activeTab === tab.key }]" @click="activeTab = tab.key">
        {{ tab.label }}
      </button>
    </section>

    <section class="table-shell">
      <StateBox v-if="loading" type="loading" message="正在讀取戰績資料..." />
      <StateBox v-else-if="error" type="error" title="讀取失敗" :message="error" />
      <StateBox v-else-if="currentRows.length === 0" title="尚未有戰績資料" message="請點擊更新戰績同步資料。" />
      <div v-else class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th v-for="header in headers" :key="header">{{ header }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in currentRows" :key="index">
              <td v-for="header in headers" :key="header">
                <span v-if="header === '排名'" class="rank-badge">{{ rankOf(row, index) }}</span>
                <span v-else-if="header === '球隊'" class="team-name">{{ teamNameOf(row) }}</span>
                <span v-else>{{ cellValue(row, header) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { cpblApi } from '../api/cpblApi'
import StateBox from '../components/StateBox.vue'

const tabs = [
  { key: 'h2h', label: '對戰戰績' },
  { key: 'pitching', label: '投球成績' },
  { key: 'batting', label: '打擊成績' }
]

const teams = ['味全龍', '台鋼雄鷹', '富邦悍將', '統一7-ELEVEn獅', '樂天桃猿', '中信兄弟']
const mainCols = ['出賽數', '勝-和-敗', '勝率', '勝差', '淘汰指數', '連勝/連敗']

const activeTab = ref('h2h')
const standings = ref({ h2h: [], pitching: [], batting: [] })
const loading = ref(false)
const syncing = ref(false)
const error = ref('')

const tabIndex = computed(() => tabs.findIndex(tab => tab.key === activeTab.value))
const currentRows = computed(() => standings.value?.[activeTab.value] || [])
const headers = computed(() => {
  if (activeTab.value === 'h2h') return ['排名', '球隊', ...mainCols, ...teams]
  return currentRows.value.length ? Object.keys(currentRows.value[0]) : []
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
    await cpblApi.updateStandings()
    await loadStandings()
    alert('✅ 戰績資料更新完成')
  } catch {
    alert('戰績更新失敗，請確認後端是否正常。')
  } finally {
    syncing.value = false
  }
}

onMounted(loadStandings)
</script>
