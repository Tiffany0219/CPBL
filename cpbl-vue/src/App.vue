<template>
  <div class="app-shell">
    <Sidebar :active-page="activePage" @change-page="activePage = $event" />

    <main class="main-content">
      <HomeView v-if="activePage === 'home'" @open-game="openGameDetail" />
      <NewsView v-else-if="activePage === 'news'" />
      <ScheduleView v-else-if="activePage === 'schedule'" @open-game="openGameDetail" />
      <StandingsView v-else-if="activePage === 'standings'" />
      <StatsView v-else-if="activePage === 'stats'" />
      <GachaView v-else-if="activePage === 'gacha'" />
      <LineupView v-else-if="activePage === 'lineup'" />
    </main>

    <GameDetailModal
      :visible="modalVisible"
      :game-id="selectedGameId"
      @close="modalVisible = false"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Sidebar from './components/Sidebar.vue'
import GameDetailModal from './components/GameDetailModal.vue'
import HomeView from './views/HomeView.vue'
import NewsView from './views/NewsView.vue'
import ScheduleView from './views/ScheduleView.vue'
import StandingsView from './views/StandingsView.vue'
import StatsView from './views/StatsView.vue'
import GachaView from './views/GachaView.vue'
import LineupView from './views/LineupView.vue'

const activePage = ref('home')
const modalVisible = ref(false)
const selectedGameId = ref(null)

function openGameDetail(gameId) {
  selectedGameId.value = gameId
  modalVisible.value = true
}
</script>
