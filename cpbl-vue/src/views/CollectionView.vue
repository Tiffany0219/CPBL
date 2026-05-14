<template>
  <div>
    <section class="section-header">
      <div>
        <p class="eyebrow">MY COLLECTION</p>
        <h2>球員收藏冊</h2>
        <p>整理抽卡獲得的球員，依球隊、姓名與位置快速查看收藏狀態。</p>
      </div>

      <div class="lineup-header-actions">
        <button class="btn-soft" type="button" @click="loadCollection">
          <i class="fa-solid fa-rotate"></i>
          重新整理
        </button>

        <button class="btn-soft danger" type="button" :disabled="collection.length === 0" @click="clearCollection">
          <i class="fa-solid fa-trash"></i>
          清空收藏
        </button>
      </div>
    </section>

    <section class="collection-stats">
      <article class="lineup-summary-card">
        <span>不同球員</span>
        <strong>{{ collection.length }}</strong>
      </article>

      <article class="lineup-summary-card">
        <span>卡片總數</span>
        <strong>{{ totalCards }}</strong>
      </article>

      <article class="lineup-summary-card">
        <span>收集球隊</span>
        <strong>{{ ownedTeams }}</strong>
      </article>

      <article class="lineup-summary-card">
        <span>最多收藏</span>
        <strong>{{ topTeam }}</strong>
      </article>
    </section>

    <section class="collection-panel collection-page-panel">
      <div class="lineup-panel-head">
        <div>
          <p class="eyebrow">PLAYER CARDS</p>
          <h3>我的球員卡</h3>
        </div>
        <span>{{ filteredCollection.length }} 張名單</span>
      </div>

      <div class="collection-tools">
        <div class="collection-search">
          <i class="fa-solid fa-magnifying-glass"></i>
          <input v-model="keyword" type="text" placeholder="搜尋球員、球隊或位置" />
        </div>

        <select v-model="teamFilter" class="collection-filter">
          <option value="">全部球隊</option>
          <option v-for="team in teams" :key="team" :value="team">{{ team }}</option>
        </select>
      </div>

      <StateBox
        v-if="collection.length === 0"
        title="收藏冊還是空的"
        message="先到球員抽卡頁抽幾張卡，這裡就會自動建立收藏。"
      />

      <StateBox
        v-else-if="filteredCollection.length === 0"
        title="找不到符合條件的球員"
        message="換個關鍵字或切換球隊篩選看看。"
      />

      <div v-else class="collection-page-grid">
        <article
          v-for="player in filteredCollection"
          :key="cleanName(player)"
          class="collection-card-large"
          :style="{ '--team-color': teamColor(player.team) }"
        >
          <div class="collection-card-top">
            <span>{{ player.team || '未知球隊' }}</span>
            <strong>x{{ player.count || 1 }}</strong>
          </div>

          <div class="collection-card-avatar">
            <img
              v-if="!failedImages[cleanName(player)]"
              :src="playerImage(player)"
              :alt="cleanName(player)"
              @error="markImageFailed(player)"
            />
            <span v-else>{{ initials(player) }}</span>
          </div>

          <div class="collection-card-body">
            <h3>{{ cleanName(player) }}</h3>
            <p>{{ player.position || '未知位置' }}</p>
          </div>

          <div class="collection-card-actions">
            <button type="button" @click="copyPlayerName(player)">
              <i class="fa-solid fa-copy"></i>
              複製姓名
            </button>

            <button class="danger" type="button" @click="removePlayer(player)">
              <i class="fa-solid fa-trash"></i>
              移除
            </button>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, inject, onMounted, ref } from 'vue'
import { API_BASE } from '../api/cpblApi'
import StateBox from '../components/StateBox.vue'
import {
  TEAMS,
  cleanPlayerName,
  clearPlayerCollection,
  getCollectionList,
  playerInitials,
  removePlayerFromCollection,
  teamColor
} from '../composables/usePlayerCollection'

const ASSET_BASE = API_BASE.replace(/\/api$/, '')
const notify = inject('notify', () => {})
const collection = ref([])
const keyword = ref('')
const teamFilter = ref('')
const failedImages = ref({})
const teams = TEAMS

const filteredCollection = computed(() => {
  const text = keyword.value.trim().toLowerCase()

  return collection.value.filter(player => {
    const content = `${cleanName(player)} ${player.team || ''} ${player.position || ''}`.toLowerCase()
    const matchesText = !text || content.includes(text)
    const matchesTeam = !teamFilter.value || player.team === teamFilter.value

    return matchesText && matchesTeam
  })
})

const totalCards = computed(() => collection.value.reduce((sum, player) => sum + Number(player.count || 1), 0))
const ownedTeams = computed(() => new Set(collection.value.map(player => player.team).filter(Boolean)).size)
const topTeam = computed(() => {
  const counts = {}
  collection.value.forEach(player => {
    const team = player.team || '未知'
    counts[team] = (counts[team] || 0) + Number(player.count || 1)
  })

  const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]
  return top ? top[0] : '-'
})

function cleanName(player) {
  return cleanPlayerName(player)
}

function initials(player) {
  return playerInitials(player)
}

function playerImage(player) {
  return `${ASSET_BASE}/static/image/players/${encodeURIComponent(cleanName(player))}.png`
}

function markImageFailed(player) {
  failedImages.value = {
    ...failedImages.value,
    [cleanName(player)]: true
  }
}

function loadCollection() {
  collection.value = getCollectionList()
}

function removePlayer(player) {
  const confirmed = confirm(`確定要移除 ${cleanName(player)} 嗎？`)
  if (!confirmed) return

  removePlayerFromCollection(cleanName(player))
  loadCollection()
}

function clearCollection() {
  const confirmed = confirm('確定要清空整本球員收藏冊嗎？')
  if (!confirmed) return

  clearPlayerCollection()
  loadCollection()
}

async function copyPlayerName(player) {
  const name = cleanName(player)

  try {
    await navigator.clipboard.writeText(name)
    notify({ type: 'success', title: '已複製', message: `${name} 已複製到剪貼簿。` })
  } catch {
    notify({ type: 'info', title: '球員姓名', message: name })
  }
}

onMounted(loadCollection)
</script>
