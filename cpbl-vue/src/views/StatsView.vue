<template>
  <div>
    <section class="section-header">
      <div>
        <p class="eyebrow">ANALYTICS</p>
        <h2>數據統計</h2>
        <p>以視覺化卡片呈現賽程、球隊與比賽資料統計。</p>
      </div>
    </section>

    <section class="stats-grid">
      <StateBox v-if="loading" type="loading" message="正在計算統計資料..." />
      <article v-for="card in cards" v-else :key="card.label" class="stat-card">
        <div class="stat-icon"><i :class="card.icon"></i></div>
        <div>
          <p>{{ card.label }}</p>
          <strong>{{ card.value }}</strong>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { cpblApi } from '../api/cpblApi'
import StateBox from '../components/StateBox.vue'

const loading = ref(false)
const cards = ref([])

onMounted(async () => {
  loading.value = true
  try {
    const games = await cpblApi.getGames()
    const teamCount = {}
    games.forEach(g => {
      if (g.away) teamCount[g.away] = (teamCount[g.away] || 0) + 1
      if (g.home) teamCount[g.home] = (teamCount[g.home] || 0) + 1
    })
    const mostActiveTeam = Object.entries(teamCount).sort((a, b) => b[1] - a[1])[0]
    cards.value = [
      { label: '總賽事數', value: games.length, icon: 'fa-solid fa-calendar-days' },
      { label: '已完成比賽', value: games.filter(g => g.status === 'FINISH').length, icon: 'fa-solid fa-flag-checkered' },
      { label: 'LIVE 比賽', value: games.filter(g => g.status === 'LIVE').length, icon: 'fa-solid fa-circle-play' },
      { label: '延賽場次', value: games.filter(g => g.status === '延賽' || g.status === 'POSTPONED').length, icon: 'fa-solid fa-cloud-rain' },
      { label: '出賽最多球隊', value: mostActiveTeam ? mostActiveTeam[0] : '-', icon: 'fa-solid fa-people-group' },
      { label: '資料來源', value: 'CPBL', icon: 'fa-solid fa-database' }
    ]
  } catch {
    cards.value = [
      { label: '總賽事數', value: '-', icon: 'fa-solid fa-calendar-days' },
      { label: '資料狀態', value: 'API 未連線', icon: 'fa-solid fa-database' }
    ]
  } finally {
    loading.value = false
  }
})
</script>
