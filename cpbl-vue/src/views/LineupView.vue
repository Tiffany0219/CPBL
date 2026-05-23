<template>
  <div>
    <section class="section-header">
      <div>
        <p class="eyebrow">MY LINEUP</p>
        <h2>我的打線</h2>
        <p>使用抽卡收藏的球員建立先發名單，重新整理後也會保留。</p>
      </div>

      <div class="lineup-header-actions">
        <button class="btn-soft" type="button" @click="reloadCollection">
          <i class="fa-solid fa-rotate"></i>
          重新整理收藏
        </button>

        <button class="btn-soft" type="button" :disabled="filledCount === 0" @click="generateShareImage">
          <i class="fa-solid fa-image"></i>
          產生分享圖
        </button>

        <button class="btn-soft danger" type="button" :disabled="filledCount === 0 || lineupSaving" @click="clearLineup">
          <i class="fa-solid fa-trash"></i>
          清空打線
        </button>
      </div>
    </section>

    <section class="lineup-summary-grid">
      <article class="lineup-summary-card">
        <span>收藏球員</span>
        <strong>{{ collection.length }}</strong>
      </article>

      <article class="lineup-summary-card">
        <span>已排棒次</span>
        <strong>{{ filledCount }}/9</strong>
      </article>

      <article class="lineup-summary-card">
        <span>目前棒次</span>
        <strong>第 {{ activeSlot.order }} 棒</strong>
      </article>

      <article class="lineup-summary-card">
        <span>同步狀態</span>
        <strong>{{ lineupStatus }}</strong>
      </article>
    </section>

    <section class="lineup-layout">
      <div class="lineup-board">
        <div class="lineup-panel-head">
          <div>
            <p class="eyebrow">STARTING NINE</p>
            <h3>先發打線</h3>
          </div>
          <span>{{ filledCount === 9 ? '完整打線' : `尚缺 ${9 - filledCount} 人` }}</span>
        </div>

        <div class="lineup-slots">
          <article
            v-for="(slot, index) in lineup"
            :key="slot.order"
            :class="['lineup-slot', { active: activeSlotIndex === index, filled: slot.player }]"
            @click="activeSlotIndex = index"
          >
            <div class="lineup-order">{{ slot.order }}</div>

            <PlayerAvatar v-if="slot.player" :player="slot.player" />
            <div v-else class="lineup-avatar empty">
              <i class="fa-solid fa-user-plus"></i>
            </div>

            <div class="lineup-slot-main">
              <strong>{{ slot.player ? cleanName(slot.player) : '尚未選擇球員' }}</strong>
              <small>{{ slot.player?.team || '從右側收藏冊加入' }}</small>
            </div>

            <select v-model="slot.defense" class="lineup-position" @click.stop @change="saveLineup">
              <option value="">位置</option>
              <option v-for="position in positions" :key="position" :value="position">
                {{ position }}
              </option>
            </select>

            <div class="lineup-slot-actions" @click.stop>
              <button class="lineup-icon-btn" type="button" :disabled="index === 0" title="上移" @click="swapSlots(index, index - 1)">
                <i class="fa-solid fa-chevron-up"></i>
              </button>

              <button class="lineup-icon-btn" type="button" :disabled="index === lineup.length - 1" title="下移" @click="swapSlots(index, index + 1)">
                <i class="fa-solid fa-chevron-down"></i>
              </button>

              <button class="lineup-icon-btn danger" type="button" :disabled="!slot.player" title="移除" @click="removeFromSlot(index)">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>
          </article>
        </div>
      </div>

      <div class="collection-panel">
        <div class="lineup-panel-head">
          <div>
            <p class="eyebrow">CARD COLLECTION</p>
            <h3>球員收藏冊</h3>
          </div>
          <span>{{ filteredCollection.length }} 位</span>
        </div>

        <div class="collection-tools">
          <div class="collection-search">
            <i class="fa-solid fa-magnifying-glass"></i>
            <input v-model="keyword" type="text" placeholder="搜尋球員或球隊" />
          </div>

          <select v-model="teamFilter" class="collection-filter">
            <option value="">全部球隊</option>
            <option v-for="team in teams" :key="team" :value="team">{{ team }}</option>
          </select>
        </div>

        <StateBox
          v-if="collection.length === 0"
          title="尚未有球員收藏"
          message="先到球員抽卡頁抽幾張卡，這裡就會出現可排進打線的球員。"
        />

        <StateBox
          v-else-if="filteredCollection.length === 0"
          title="查無符合球員"
          message="換個關鍵字或球隊篩選看看。"
        />

        <div v-else class="collection-grid">
          <article
            v-for="player in filteredCollection"
            :key="cleanName(player)"
            :class="['collection-player-card', { selected: isInLineup(player) }]"
            :style="{ '--team-color': teamColor(player.team) }"
          >
            <PlayerAvatar :player="player" />

            <div class="collection-player-info">
              <strong>{{ cleanName(player) }}</strong>
              <span>{{ player.team || '未知球隊' }} · {{ player.position || '未知位置' }}</span>
              <small>持有 {{ player.count || 1 }} 張</small>
            </div>

            <button class="lineup-add-btn" type="button" @click="addToLineup(player)">
              <i :class="isInLineup(player) ? 'fa-solid fa-check' : 'fa-solid fa-plus'"></i>
              {{ isInLineup(player) ? '已加入' : '加入' }}
            </button>
          </article>
        </div>
      </div>
    </section>

    <div v-if="shareImage" class="modal">
      <div class="modal-content lineup-share-modal">
        <button class="modal-close" type="button" @click="shareImage = ''">&times;</button>
        <p class="eyebrow">LINEUP SHARE</p>
        <h3>我的先發打線分享圖</h3>
        <img :src="shareImage" alt="我的先發打線分享圖" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, inject, onMounted, ref, watch } from 'vue'
import { API_BASE, cpblApi } from '../api/cpblApi'
import StateBox from '../components/StateBox.vue'
import {
  TEAMS,
  cleanPlayerName,
  getCollectionList,
  normalizePlayer as normalizeCollectionPlayer,
  playerInitials,
  teamColor as getTeamColor
} from '../composables/usePlayerCollection'

const LINEUP_KEY = 'my_cpbl_lineup'
const ASSET_BASE = API_BASE.replace(/\/api$/, '')
const auth = inject('auth', null)
const notify = inject('notify', () => {})
const confirmAction = inject('confirmAction', async () => false)

const positions = ['投手', '捕手', '一壘', '二壘', '三壘', '游擊', '左外野', '中外野', '右外野', '指定打擊']
const defaultPositions = ['中外野', '二壘', '游擊', '一壘', '三壘', '左外野', '右外野', '捕手', '指定打擊']
const teams = TEAMS

const collection = ref([])
const lineup = ref(createEmptyLineup())
const activeSlotIndex = ref(0)
const keyword = ref('')
const teamFilter = ref('')
const failedImages = ref({})
const lineupSaving = ref(false)
const lineupSyncedAt = ref('')
const shareImage = ref('')

const activeSlot = computed(() => lineup.value[activeSlotIndex.value] || lineup.value[0])
const filledCount = computed(() => lineup.value.filter(slot => slot.player).length)
const lineupStatus = computed(() => {
  if (!auth?.token?.value) return '本機'
  if (lineupSaving.value) return '同步中'
  return lineupSyncedAt.value ? '已同步' : '帳號'
})
const lineupStorageKey = computed(() => {
  const userId = auth?.user?.value?.id
  return userId ? `${LINEUP_KEY}_${userId}` : LINEUP_KEY
})
const filteredCollection = computed(() => {
  const searchText = keyword.value.trim().toLowerCase()

  return collection.value.filter(player => {
    const content = `${cleanName(player)} ${player.team || ''} ${player.position || ''}`.toLowerCase()
    const matchesKeyword = !searchText || content.includes(searchText)
    const matchesTeam = !teamFilter.value || player.team === teamFilter.value

    return matchesKeyword && matchesTeam
  })
})

const PlayerAvatar = defineComponent({
  props: {
    player: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    return () => {
      const name = cleanName(props.player)
      const imageFailed = failedImages.value[name]
      const style = { '--team-color': teamColor(props.player.team) }

      return h('div', { class: 'lineup-avatar', style }, [
        !imageFailed
          ? h('img', {
              src: playerImage(name),
              alt: name,
              onError: () => markImageFailed(name)
            })
          : h('span', initials(name))
      ])
    }
  }
})

function createEmptyLineup() {
  return Array.from({ length: 9 }, (_, index) => ({
    order: index + 1,
    defense: defaultPositions[index],
    player: null
  }))
}

function cleanName(playerOrName = '') {
  return cleanPlayerName(playerOrName)
}

function initials(name = '') {
  return playerInitials(name)
}

function playerImage(name) {
  return `${ASSET_BASE}/static/image/players/${encodeURIComponent(name)}.png`
}

function markImageFailed(name) {
  failedImages.value = {
    ...failedImages.value,
    [name]: true
  }
}

function teamColor(team = '') {
  return getTeamColor(team)
}

function normalizePlayer(player, fallbackName = '') {
  return normalizeCollectionPlayer(player, fallbackName)
}

async function loadCollection() {
  if (auth?.token?.value) {
    try {
      const cards = await cpblApi.getUserCards(auth.token.value)
      collection.value = cards.map(card => normalizePlayer(card))
      return
    } catch {
      notify({ type: 'warning', title: '收藏同步失敗', message: '暫時改用本機收藏資料。' })
    }
  }
  collection.value = getCollectionList()
}

async function loadLineup() {
  if (auth?.token?.value) {
    try {
      const result = await cpblApi.getLineup(auth.token.value)
      applySavedLineup(result?.slots || [])
      lineupSyncedAt.value = result?.updatedAt || ''
      return
    } catch {
      notify({ type: 'warning', title: '打線同步失敗', message: '暫時改用本機打線。' })
    }
  }

  let saved = []
  try {
    saved = JSON.parse(localStorage.getItem(lineupStorageKey.value) || '[]')
  } catch {
    saved = []
  }

  applySavedLineup(saved)
}

function applySavedLineup(saved) {
  if (!Array.isArray(saved) || saved.length === 0) {
    lineup.value = createEmptyLineup()
    return
  }

  const empty = createEmptyLineup()
  lineup.value = empty.map((slot, index) => {
    const savedSlot = saved[index] || {}

    return {
      order: slot.order,
      defense: savedSlot.defense || slot.defense,
      player: savedSlot.player ? normalizePlayer(savedSlot.player) : null
    }
  })
}

async function saveLineup() {
  localStorage.setItem(lineupStorageKey.value, JSON.stringify(lineup.value))
  if (!auth?.token?.value) return

  lineupSaving.value = true
  try {
    const result = await cpblApi.saveLineup(lineup.value, auth.token.value)
    lineupSyncedAt.value = result?.updatedAt || new Date().toISOString()
  } catch {
    notify({ type: 'warning', title: '打線未同步', message: '已先保存在本機，稍後可重新整理再試。' })
  } finally {
    lineupSaving.value = false
  }
}

async function reloadCollection() {
  await loadCollection()
}

function isInLineup(player) {
  const name = cleanName(player)
  return lineup.value.some(slot => slot.player && cleanName(slot.player) === name)
}

function addToLineup(player) {
  const normalized = normalizePlayer(player)
  const existingIndex = lineup.value.findIndex(slot => slot.player && cleanName(slot.player) === cleanName(normalized))

  if (existingIndex !== -1) {
    activeSlotIndex.value = existingIndex
    return
  }

  const emptyIndex = lineup.value.findIndex(slot => !slot.player)
  const activeSlotIsEmpty = !lineup.value[activeSlotIndex.value]?.player
  const targetIndex = activeSlotIsEmpty ? activeSlotIndex.value : emptyIndex !== -1 ? emptyIndex : activeSlotIndex.value

  lineup.value[targetIndex].player = normalized
  saveLineup()

  const nextEmptyIndex = lineup.value.findIndex((slot, index) => index > targetIndex && !slot.player)
  if (nextEmptyIndex !== -1) activeSlotIndex.value = nextEmptyIndex
}

function removeFromSlot(index) {
  lineup.value[index].player = null
  saveLineup()
}

function swapSlots(index, targetIndex) {
  if (targetIndex < 0 || targetIndex >= lineup.value.length) return

  const current = {
    defense: lineup.value[index].defense,
    player: lineup.value[index].player
  }
  const target = {
    defense: lineup.value[targetIndex].defense,
    player: lineup.value[targetIndex].player
  }

  lineup.value[index].defense = target.defense
  lineup.value[index].player = target.player
  lineup.value[targetIndex].defense = current.defense
  lineup.value[targetIndex].player = current.player
  activeSlotIndex.value = targetIndex
  saveLineup()
}

async function clearLineup() {
  const confirmed = await confirmAction({
    title: '清空打線',
    message: '確定要清空目前九人打線嗎？登入狀態下也會同步清空。',
    confirmText: '清空',
    danger: true
  })
  if (!confirmed) return

  lineup.value = createEmptyLineup()
  activeSlotIndex.value = 0
  await saveLineup()
}

function generateShareImage() {
  const canvas = document.createElement('canvas')
  canvas.width = 1080
  canvas.height = 1350
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const gradient = ctx.createLinearGradient(0, 0, 1080, 1350)
  gradient.addColorStop(0, '#081727')
  gradient.addColorStop(0.55, '#0b1f33')
  gradient.addColorStop(1, '#1f5f99')
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, 1080, 1350)

  ctx.fillStyle = 'rgba(255,255,255,0.08)'
  for (let i = 0; i < 18; i += 1) {
    ctx.beginPath()
    ctx.arc(80 + i * 62, 180 + (i % 5) * 92, 3, 0, Math.PI * 2)
    ctx.fill()
  }

  ctx.fillStyle = '#7dd3fc'
  ctx.font = '900 38px sans-serif'
  ctx.fillText('GOBASE!', 72, 92)
  ctx.fillStyle = '#ffffff'
  ctx.font = '900 64px sans-serif'
  ctx.fillText('我的先發打線', 72, 170)
  ctx.fillStyle = '#cbd5e1'
  ctx.font = '800 28px sans-serif'
  ctx.fillText(`${filledCount.value}/9 位球員 · ${lineupStatus.value}`, 72, 220)

  lineup.value.forEach((slot, index) => {
    const top = 290 + index * 105
    const player = slot.player
    const color = teamColor(player?.team)
    ctx.fillStyle = 'rgba(255,255,255,0.94)'
    roundRect(ctx, 72, top, 936, 78, 22)
    ctx.fill()

    ctx.fillStyle = color
    roundRect(ctx, 72, top, 18, 78, 22)
    ctx.fill()

    ctx.fillStyle = '#0b1f33'
    ctx.font = '900 32px sans-serif'
    ctx.fillText(`${slot.order}`, 116, top + 50)
    ctx.fillStyle = color
    ctx.font = '900 24px sans-serif'
    ctx.fillText(slot.defense || '-', 180, top + 49)
    ctx.fillStyle = '#0b1f33'
    ctx.font = '900 34px sans-serif'
    ctx.fillText(player ? cleanName(player) : '尚未選擇球員', 320, top + 48)
    ctx.fillStyle = '#64748b'
    ctx.font = '800 22px sans-serif'
    ctx.fillText(player?.team || '', 760, top + 48)
  })

  ctx.fillStyle = '#ffffff'
  ctx.font = '800 24px sans-serif'
  ctx.fillText('Generated by GoBase CPBL', 72, 1284)

  shareImage.value = canvas.toDataURL('image/png')
}

function roundRect(ctx, x, y, width, height, radius) {
  ctx.beginPath()
  ctx.moveTo(x + radius, y)
  ctx.lineTo(x + width - radius, y)
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius)
  ctx.lineTo(x + width, y + height - radius)
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height)
  ctx.lineTo(x + radius, y + height)
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius)
  ctx.lineTo(x, y + radius)
  ctx.quadraticCurveTo(x, y, x + radius, y)
  ctx.closePath()
}

watch(() => auth?.token?.value, async () => {
  await loadCollection()
  await loadLineup()
})

onMounted(async () => {
  await loadCollection()
  await loadLineup()
})
</script>
