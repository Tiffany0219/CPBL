<template>
  <div>
    <section class="section-header">
      <div>
        <p class="eyebrow">MY COLLECTION</p>
        <h2>球員收藏冊</h2>
        <p>整理抽卡獲得的球員，登入後會同步保存到你的卡牌帳號。</p>
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
          :class="['collection-card-large', player.rarity || 'common']"
          :style="{ '--team-color': teamColor(player.team) }"
          @click="selectedPlayer = player"
        >
          <div class="collection-card-top">
            <span>{{ player.team || '未知球隊' }}</span>
            <strong>{{ rarityLabel(player.rarity) }} x{{ player.count || 1 }}</strong>
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
            <button type="button" @click.stop="copyPlayerName(player)">
              <i class="fa-solid fa-copy"></i>
              複製姓名
            </button>

            <button class="danger" type="button" @click.stop="removePlayer(player)">
              <i class="fa-solid fa-trash"></i>
              移除
            </button>
          </div>
        </article>
      </div>
    </section>

    <div v-if="selectedPlayer" class="modal" style="display:block;">
      <div class="modal-content card-detail-modal">
        <button class="modal-close" type="button" @click="selectedPlayer = null">&times;</button>
        <p class="eyebrow">PLAYER CARD</p>
        <div class="card-detail-head">
          <div class="collection-card-avatar">
            <img
              v-if="!failedImages[cleanName(selectedPlayer)]"
              :src="playerImage(selectedPlayer)"
              :alt="cleanName(selectedPlayer)"
              @error="markImageFailed(selectedPlayer)"
            />
            <span v-else>{{ initials(selectedPlayer) }}</span>
          </div>
          <div>
            <span :class="['rarity-pill', selectedPlayer.rarity || 'common']">{{ rarityLabel(selectedPlayer.rarity) }}</span>
            <h2>{{ cleanName(selectedPlayer) }}</h2>
            <p>{{ selectedPlayer.team || '未知球隊' }} · {{ selectedPlayer.position || '未知位置' }}</p>
          </div>
        </div>
        <p class="card-detail-desc">{{ selectedPlayer.description || '這位球員已加入你的收藏冊，之後可以排進我的打線。' }}</p>
        <div class="profile-list-row">
          <span>持有張數</span>
          <strong>x{{ selectedPlayer.count || 1 }}</strong>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, inject, onMounted, ref, watch } from 'vue'
import { API_BASE, cpblApi } from '../api/cpblApi'
import StateBox from '../components/StateBox.vue'
import {
  TEAMS,
  cleanPlayerName,
  clearPlayerCollection,
  getCollectionList,
  playerInitials,
  rarityLabel,
  removePlayerFromCollection,
  saveCollectionMap,
  teamColor
} from '../composables/usePlayerCollection'

const ASSET_BASE = API_BASE.replace(/\/api$/, '')
const notify = inject('notify', () => {})
const auth = inject('auth', null)
const collection = ref([])
const keyword = ref('')
const teamFilter = ref('')
const failedImages = ref({})
const selectedPlayer = ref(null)
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

function collectionListToMap(cards = []) {
  return cards.reduce((map, card) => {
    map[cleanPlayerName(card)] = card
    return map
  }, {})
}

async function loadCollection() {
  if (auth?.token?.value) {
    try {
      const cards = await cpblApi.getUserCards(auth.token.value)
      saveCollectionMap(collectionListToMap(cards || []))
      collection.value = getCollectionList()
      return
    } catch {
      notify({ type: 'warning', title: '同步失敗', message: '暫時改用本機收藏資料。' })
    }
  }

  collection.value = getCollectionList()
}

async function removePlayer(player) {
  const confirmed = confirm(`確定要移除 ${cleanName(player)} 嗎？`)
  if (!confirmed) return

  if (auth?.token?.value) {
    try {
      await cpblApi.removeUserCard(cleanName(player), auth.token.value)
    } catch {
      notify({ type: 'warning', title: '移除失敗', message: '伺服器暫時沒有同步成功。' })
      return
    }
  }

  removePlayerFromCollection(cleanName(player))
  await loadCollection()
}

async function clearCollection() {
  const confirmed = confirm('確定要清空整本球員收藏冊嗎？')
  if (!confirmed) return

  if (auth?.token?.value) {
    try {
      await cpblApi.clearUserCards(auth.token.value)
    } catch {
      notify({ type: 'warning', title: '清空失敗', message: '伺服器暫時沒有同步成功。' })
      return
    }
  }

  clearPlayerCollection()
  await loadCollection()
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

if (auth?.token) {
  watch(auth.token, () => {
    loadCollection()
  })
}

onMounted(loadCollection)
</script>
