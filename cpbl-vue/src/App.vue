<template>
  <div class="app-shell">
    <Sidebar :active-page="activePage" @change-page="activePage = $event" />

    <main class="main-content">
      <HomeView v-if="activePage === 'home'" @open-game="openGameDetail" @change-page="activePage = $event" />
      <NewsView v-else-if="activePage === 'news'" />
      <ScheduleView v-else-if="activePage === 'schedule'" @open-game="openGameDetail" />
      <StandingsView v-else-if="activePage === 'standings'" />
      <StatsView v-else-if="activePage === 'stats'" />
      <SyncView v-else-if="activePage === 'sync'" />
      <GachaView v-else-if="activePage === 'gacha'" @change-page="activePage = $event" />
      <CollectionView v-else-if="activePage === 'collection'" />
      <LineupView v-else-if="activePage === 'lineup'" />
    </main>

    <GameDetailModal
      :show="modalVisible"
      :detail="selectedGameDetail"
      :loading="detailLoading"
      :error="detailError"
      @close="closeGameDetail"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { cpblApi } from './api/cpblApi'
import Sidebar from './components/Sidebar.vue'
import GameDetailModal from './components/GameDetailModal.vue'
import HomeView from './views/HomeView.vue'
import NewsView from './views/NewsView.vue'
import ScheduleView from './views/ScheduleView.vue'
import StandingsView from './views/StandingsView.vue'
import StatsView from './views/StatsView.vue'
import SyncView from './views/SyncView.vue'
import GachaView from './views/GachaView.vue'
import CollectionView from './views/CollectionView.vue'
import LineupView from './views/LineupView.vue'

const activePage = ref('home')
const modalVisible = ref(false)
const selectedGameDetail = ref(null)
const detailLoading = ref(false)
const detailError = ref('')

async function openGameDetail(gameId) {
  modalVisible.value = true
  selectedGameDetail.value = null
  detailError.value = ''
  detailLoading.value = true

  try {
    selectedGameDetail.value = await cpblApi.getGameDetail(gameId)
  } catch (err) {
    console.error(err)
    detailError.value = '無法取得比賽詳細資料，請確認後端 /api/game/detail 是否正常。'
  } finally {
    detailLoading.value = false
  }
}

function closeGameDetail() {
  modalVisible.value = false
  selectedGameDetail.value = null
  detailError.value = ''
}
</script>
