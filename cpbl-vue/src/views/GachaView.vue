<template>
  <div>
    <section class="section-header">
      <div>
        <p class="eyebrow">PLAYER CARD</p>
        <h2>球員抽卡</h2>
        <p>從球員池隨機抽取球員卡，建立更有互動性的中職資料體驗。</p>
      </div>
      <div class="lineup-header-actions">
        <button class="btn-soft" type="button" @click="$emit('change-page', 'collection')">
          <i class="fa-solid fa-layer-group"></i>
          查看收藏冊
        </button>

        <button class="btn-primary" :disabled="loading" @click="drawCard">
          <i :class="loading ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-bolt'"></i>
          {{ loading ? '抽卡中' : '立即抽卡' }}
        </button>
      </div>
    </section>

    <section class="gacha-layout">
      <div class="gacha-panel">
        <div class="search-box">
          <input v-model="keyword" type="text" placeholder="輸入球員姓名搜尋..." @keyup.enter="searchPlayer" />
          <button type="button" @click="searchPlayer"><i class="fa-solid fa-magnifying-glass"></i></button>
        </div>

        <div class="gacha-note">
          <h3>抽卡說明</h3>
          <p>系統會從球員池中隨機抽取一位球員，並依球隊產生對應卡牌樣式。</p>
          <p>抽到的球員會自動存入瀏覽器 localStorage，可作為簡易集卡冊基礎。</p>
        </div>
      </div>

      <div class="gacha-stage">
        <StateBox v-if="loading" type="loading" message="正在聯繫球探中..." />
        <StateBox v-else-if="error" type="error" title="抽卡失敗" :message="error" />
        <article v-else-if="player" class="player-card-site" :style="{ '--team-color': teamColor }">
          <div class="player-card-top">
            <span>{{ isRare ? 'LIMITED EDITION' : 'CPBL PLAYER CARD' }}</span>
            <strong>{{ isRare ? 'LEGEND' : 'STANDARD' }}</strong>
          </div>
          <div class="player-photo-wrap">
            <img
              v-if="!imageMissing"
              :src="playerImage"
              :alt="cleanName"
              @error="imageMissing = true"
            />
            <div v-else class="player-photo-fallback">
              {{ playerInitials }}
            </div>
          </div>
          <div class="player-card-info">
            <h3>{{ cleanName }}</h3>
            <p>{{ player.team || '未知球隊' }} · {{ player.position || '未知位置' }}</p>
          </div>
          <div class="player-card-desc">
            {{ player.description || '這位球員在場上展現穩定表現，是球隊不可或缺的戰力。' }}
          </div>
          <div class="player-card-footer">
            <span>{{ isRare ? '★★★ 傳說球員' : '★ 一般球員' }}</span>
          </div>
        </article>
        <div v-else class="card-display-empty">
          <i class="fa-regular fa-id-card"></i>
          <h3>尚未抽卡</h3>
          <p>點擊「立即抽卡」開始抽取你的球員卡牌。</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { API_BASE, cpblApi } from '../api/cpblApi'
import StateBox from '../components/StateBox.vue'
import {
  addPlayerToCollection,
  cleanPlayerName,
  playerInitials as getPlayerInitials,
  teamColor as getTeamColor
} from '../composables/usePlayerCollection'

defineEmits(['change-page'])

const keyword = ref('')
const player = ref(null)
const loading = ref(false)
const error = ref('')
const imageMissing = ref(false)
const ASSET_BASE = API_BASE.replace(/\/api$/, '')

const cleanName = computed(() => cleanPlayerName(player.value))
const isRare = computed(() => cleanName.value.includes('頌恩'))
const teamColor = computed(() => getTeamColor(player.value?.team))
const playerInitials = computed(() => getPlayerInitials(player.value))
const playerImage = computed(() => `${ASSET_BASE}/static/image/players/${encodeURIComponent(cleanName.value)}.png`)

function saveToInventory(p) {
  addPlayerToCollection(p)
}

async function getPool() {
  const players = await cpblApi.getPlayerPool()
  if (!Array.isArray(players) || players.length === 0) throw new Error('球員池沒有資料')
  return players
}

async function drawCard() {
  loading.value = true
  error.value = ''
  player.value = null
  imageMissing.value = false
  try {
    const players = await getPool()
    const filtered = players.filter(p => {
      const team = p.team || ''
      const name = p.name || ''
      return !team.includes('二軍') || name.includes('頌恩')
    })
    const pool = filtered.length ? filtered : players
    const luckyPlayer = pool[Math.floor(Math.random() * pool.length)]
    player.value = luckyPlayer
    imageMissing.value = false
    saveToInventory(luckyPlayer)
  } catch {
    error.value = '請確認 Flask 是否啟動，以及 /api/get_player_pool 是否正常回傳資料。'
  } finally {
    loading.value = false
  }
}

async function searchPlayer() {
  if (!keyword.value.trim()) {
    alert('請輸入球員姓名')
    return
  }
  loading.value = true
  error.value = ''
  player.value = null
  imageMissing.value = false
  try {
    const players = await getPool()
    const found = players.find(p => (p.name || '').replace(/\*/g, '').includes(keyword.value.trim()))
    if (!found) {
      error.value = '找不到球員，請確認姓名是否正確，或先同步球員資料。'
      return
    }
    player.value = found
    imageMissing.value = false
  } catch {
    error.value = '搜尋失敗，請確認球員 API 是否正常。'
  } finally {
    loading.value = false
  }
}
</script>
