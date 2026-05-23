<template>
  <div class="gacha-page">
    <section class="section-header gacha-header">
      <div>
        <p class="eyebrow">PLAYER CARD</p>
        <h2>球員抽卡</h2>
        <p>開啟今日球員包，抽到的卡牌會依稀有度產生不同卡面與收藏紀錄。</p>
      </div>
      <div class="lineup-header-actions">
        <button class="btn-soft" type="button" @click="$emit('change-page', 'collection')">
          <i class="fa-solid fa-layer-group"></i>
          查看收藏冊
        </button>

        <button class="btn-primary" :disabled="isDrawing" @click="drawCard">
          <i :class="isDrawing ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-wand-magic-sparkles'"></i>
          {{ isDrawing ? '開包中' : '開一包' }}
        </button>
      </div>
    </section>

    <section class="gacha-layout">
      <div class="gacha-panel">
        <div class="pack-console">
          <div class="pack-icon">
            <i class="fa-solid fa-box-open"></i>
          </div>
          <div>
            <span>DAILY PLAYER PACK</span>
            <strong>{{ packTitle }}</strong>
            <small>登入後自動入庫</small>
          </div>
        </div>

        <div class="search-box">
          <input v-model="keyword" type="text" placeholder="輸入球員姓名搜尋..." @keyup.enter="searchPlayer" />
          <button type="button" @click="searchPlayer"><i class="fa-solid fa-magnifying-glass"></i></button>
        </div>

        <div class="gacha-note">
          <h3>抽卡說明</h3>
          <p>系統會從球員池中隨機抽取一位球員，並依球隊產生對應卡牌樣式。</p>
          <p>抽卡需要登入，抽到的球員會自動同步保存到你的卡牌帳號。</p>
        </div>

        <div class="pack-mode-toggle">
          <button
            v-for="mode in packModes"
            :key="mode.key"
            type="button"
            :class="{ active: packMode === mode.key }"
            :disabled="isDrawing"
            @click="packMode = mode.key"
          >
            <i :class="mode.icon"></i>
            <span>{{ mode.label }}</span>
            <small>{{ mode.text }}</small>
          </button>
        </div>

        <div class="rarity-odds">
          <div v-for="item in odds" :key="item.key" :class="['odds-row', item.key]">
            <span>{{ item.label }}</span>
            <strong>{{ item.rate }}</strong>
          </div>
        </div>

        <div class="point-shop-card">
          <div class="point-shop-head">
            <div>
              <span>POINT SHOP</span>
              <strong>{{ cardPoints }} 點</strong>
            </div>
            <i class="fa-solid fa-coins"></i>
          </div>
          <button
            v-for="pack in pointPacks"
            :key="pack.key"
            type="button"
            :disabled="isDrawing || cardPoints < pack.cost"
            @click="openPointPack(pack.key)"
          >
            <span>{{ pack.label }}</span>
            <b>{{ pack.cost }} 點</b>
          </button>
        </div>

        <div v-if="recentDraws.length" class="recent-draws">
          <div class="recent-draws-head">
            <span>最近抽到</span>
            <button type="button" @click="recentDraws = []">清除</button>
          </div>
          <div v-for="item in recentDraws" :key="`${item.name}-${item.drawnAt}`" :class="['recent-draw-item', item.rarity]">
            <span>{{ rarityLabel(item.rarity) }}</span>
            <strong>{{ item.name }}</strong>
            <small>{{ item.team || '未知球隊' }}</small>
          </div>
        </div>
      </div>

      <div :class="['gacha-stage', { opening, revealed: player && !opening, jackpot: isChaseCard && !opening }]">
        <div class="stage-rim" aria-hidden="true"></div>
        <div class="stage-rays" aria-hidden="true"></div>
        <div v-if="opening || player" class="stage-particles" aria-hidden="true">
          <span v-for="n in 12" :key="n" :style="{ '--i': n }"></span>
        </div>

        <div v-if="opening" class="pack-opening">
          <div class="pack-card-stack">
            <span></span>
            <span></span>
            <strong>
              <i class="fa-solid fa-baseball"></i>
              GOBASE
            </strong>
          </div>
          <div class="opening-status">
            <span>{{ openingStepLabel }}</span>
            <h3>{{ openingTitle }}</h3>
            <p>{{ openingMessage }}</p>
          </div>
        </div>

        <StateBox v-else-if="loading" type="loading" message="正在聯繫球探中..." />
        <StateBox v-else-if="error" type="error" title="抽卡失敗" :message="error" />
        <div v-else-if="player" :key="drawKey" class="gacha-result-shell">
        <article
          :class="['player-card-site', rarityClass]"
          :style="{ '--team-color': teamColor }"
        >
          <div class="holo-layer" aria-hidden="true"></div>
          <div class="card-inner-frame" aria-hidden="true"></div>
          <div class="rarity-medallion">
            <span>{{ rarityStars }}</span>
            <strong>{{ rarityText }}</strong>
          </div>
          <div class="player-card-top">
            <span>{{ rarityHeadline }}</span>
            <strong>{{ rarityText }}</strong>
          </div>
          <div class="player-card-serial">
            <span>{{ cardSerial }}</span>
            <b>{{ rarityStars }}</b>
          </div>
          <div class="player-photo-wrap">
            <div class="player-photo-label">
              <i class="fa-solid fa-baseball-bat-ball"></i>
              TEAM SERIES
            </div>
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
          <div class="player-card-stats">
            <span>
              <small>TEAM</small>
              <b>{{ player.team || '未知' }}</b>
            </span>
            <span>
              <small>POS</small>
              <b>{{ player.position || '未知' }}</b>
            </span>
            <span>
              <small>TYPE</small>
              <b>{{ rarityText }}</b>
            </span>
          </div>
          <div class="player-card-desc">
            {{ player.description || '這位球員在場上展現穩定表現，是球隊不可或缺的戰力。' }}
          </div>
          <div class="player-card-footer">
            <span>{{ rarityStars }} {{ rarityText }}球員</span>
            <button type="button" :disabled="isDrawing" @click="drawCard">
              再開一包
            </button>
          </div>
        </article>
        <aside class="cheer-player-card">
          <div class="cheer-player-head">
            <span>CHEER STAGE</span>
            <strong>{{ cheerSong.title }}</strong>
          </div>

          <div v-if="cheerSong.hasVideo" class="cheer-video-frame">
            <iframe
              v-if="cheerPlayerReady"
              :src="cheerEmbedUrl"
              title="球員應援曲播放器"
              allow="autoplay; encrypted-media; picture-in-picture"
              allowfullscreen
            ></iframe>
            <button v-else type="button" @click="playCheerSong">
              <i class="fa-solid fa-play"></i>
              播放應援曲
            </button>
          </div>

          <div v-else class="cheer-empty-state">
            <i class="fa-solid fa-music"></i>
            <h3>尚未收錄應援曲</h3>
            <p>貼上 YouTube 連結或影片 ID，這位球員下次抽到就會直接播放。</p>
            <form class="cheer-link-form" @submit.prevent="saveCheerLink">
              <input v-model="cheerVideoInput" type="text" placeholder="貼上 YouTube 連結或影片 ID" />
              <button type="submit">
                <i class="fa-solid fa-plus"></i>
                收錄
              </button>
            </form>
          </div>

          <div class="cheer-player-actions">
            <button v-if="cheerSong.hasVideo" type="button" @click="playCheerSong">
              <i class="fa-solid fa-volume-high"></i>
              重新播放
            </button>
            <a :href="cheerSong.searchUrl" target="_blank" rel="noreferrer">
              <i class="fa-brands fa-youtube"></i>
              YouTube 搜尋
            </a>
          </div>
        </aside>
        </div>
        <div v-else class="card-display-empty">
          <div class="empty-pack-preview">
            <i class="fa-solid fa-baseball"></i>
            <span>GOBASE PACK</span>
          </div>
          <h3>尚未開包</h3>
          <p>點擊「開一包」開始抽取你的球員卡牌。</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, inject, ref } from 'vue'
import { API_BASE, cpblApi } from '../api/cpblApi'
import StateBox from '../components/StateBox.vue'
import { resolveCheerSong, saveCheerOverride, youtubeEmbedUrl } from '../composables/useCheerSong'
import {
  addPlayerToCollection,
  cleanPlayerName,
  playerRarity,
  playerInitials as getPlayerInitials,
  rarityLabel,
  teamColor as getTeamColor
} from '../composables/usePlayerCollection'

defineEmits(['change-page'])

const notify = inject('notify', () => {})
const auth = inject('auth', null)
const keyword = ref('')
const player = ref(null)
const loading = ref(false)
const opening = ref(false)
const openingStep = ref('idle')
const error = ref('')
const imageMissing = ref(false)
const cheerPlayerReady = ref(false)
const cheerOverrideVersion = ref(0)
const cheerVideoInput = ref('')
const drawKey = ref(0)
const recentDraws = ref([])
const ASSET_BASE = API_BASE.replace(/\/api$/, '')

const packMode = ref('standard')
const packModes = [
  { key: 'standard', label: '標準包', text: '穩定收藏', icon: 'fa-solid fa-box' },
  { key: 'premium', label: '高級包', text: '稀有加成', icon: 'fa-solid fa-gem' }
]
const pointPacks = [
  { key: 'standard', label: '點數標準包', cost: 18 },
  { key: 'premium', label: '點數高級包', cost: 60 }
]
const odds = computed(() => packMode.value === 'premium'
  ? [
      { key: 'common', label: '一般', rate: '45%' },
      { key: 'rare', label: '稀有', rate: '35%' },
      { key: 'holo', label: '閃卡', rate: '14%' },
      { key: 'legend', label: '傳說', rate: '6%' }
    ]
  : [
      { key: 'common', label: '一般', rate: '70%' },
      { key: 'rare', label: '稀有', rate: '20%' },
      { key: 'holo', label: '閃卡', rate: '7%' },
      { key: 'legend', label: '傳說', rate: '3%' }
    ]
)

const cleanName = computed(() => cleanPlayerName(player.value))
const rarity = computed(() => playerRarity(player.value || {}))
const rarityText = computed(() => rarityLabel(rarity.value))
const rarityClass = computed(() => ({
  rare: rarity.value === 'rare',
  holo: rarity.value === 'holo',
  legend: rarity.value === 'legend'
}))
const rarityHeadline = computed(() => {
  if (rarity.value === 'legend') return 'LIMITED EDITION'
  if (rarity.value === 'holo') return 'HOLO FOIL'
  if (rarity.value === 'rare') return 'RARE CARD'
  return 'CPBL PLAYER CARD'
})
const rarityStars = computed(() => ({ common: '★', rare: '★★', holo: '✦✦✦', legend: '★★★' }[rarity.value] || '★'))
const teamColor = computed(() => getTeamColor(player.value?.team))
const playerInitials = computed(() => getPlayerInitials(player.value))
const playerImage = computed(() => `${ASSET_BASE}/static/image/players/${encodeURIComponent(cleanName.value)}.png`)
const cheerSong = computed(() => {
  cheerOverrideVersion.value
  return resolveCheerSong(player.value || {})
})
const cheerEmbedUrl = computed(() => youtubeEmbedUrl(cheerSong.value.youtubeId))
const isDrawing = computed(() => loading.value || opening.value)
const isChaseCard = computed(() => ['holo', 'legend'].includes(rarity.value))
const cardPoints = computed(() => auth?.user?.value?.card_points || 0)
const packTitle = computed(() => {
  if (opening.value) return '開包中'
  if (player.value) return `${rarityText.value}球員已入手`
  return packMode.value === 'premium' ? '高級球員包' : '今日球員包'
})
const openingTitle = computed(() => ({
  shuffle: '球員包啟封',
  scout: '球探名單確認',
  reveal: '卡牌揭曉中'
}[openingStep.value] || '球員包開啟中'))
const openingMessage = computed(() => ({
  shuffle: '正在洗牌與切包，建立今日抽選序列...',
  scout: '比對球員池、球隊與稀有度權重...',
  reveal: '最後一道封膜即將打開。'
}[openingStep.value] || '正在準備球員包...'))
const openingStepLabel = computed(() => ({
  shuffle: 'STEP 01',
  scout: 'STEP 02',
  reveal: 'STEP 03'
}[openingStep.value] || 'READY'))
const cardSerial = computed(() => {
  const id = cleanName.value
    ? Array.from(cleanName.value).reduce((sum, char) => sum + char.charCodeAt(0), 0)
    : 0
  return `CPBL-${String(id % 9999).padStart(4, '0')}`
})

async function saveToInventory(p) {
  if (!auth?.token?.value) {
    throw new Error('AUTH_REQUIRED')
  }

  try {
    const card = { ...p, rarity: playerRarity(p) }
    await cpblApi.saveUserCard(card, auth.token.value)
    addPlayerToCollection(card)
    try {
      await auth.refreshCards?.()
    } catch {
      notify({ type: 'warning', title: '同步提醒', message: '卡牌已儲存，收藏冊稍後重新整理即可更新。' })
    }
  } catch {
    throw new Error('SAVE_FAILED')
  }
}

async function getPool() {
  const players = await cpblApi.getPlayerPool()
  if (!Array.isArray(players) || players.length === 0) throw new Error('球員池沒有資料')
  return players
}

async function drawCard() {
  loading.value = true
  opening.value = true
  openingStep.value = 'shuffle'
  error.value = ''
  player.value = null
  cheerPlayerReady.value = false
  cheerVideoInput.value = ''
  imageMissing.value = false
  try {
    const players = await getPool()
    await delay(420)
    openingStep.value = 'scout'
    await delay(380)
    const filtered = players.filter(p => {
      const team = p.team || ''
      const name = p.name || ''
      return !team.includes('二軍') || name.includes('頌恩')
    })
    const pool = filtered.length ? filtered : players
    const luckyPlayer = pool[Math.floor(Math.random() * pool.length)]
    openingStep.value = 'reveal'
    await delay(420)
    player.value = { ...luckyPlayer, rarity: rollRarity(luckyPlayer) }
    drawKey.value += 1
    imageMissing.value = false
    playCheerSong()
    await saveToInventory(player.value)
    addRecentDraw(player.value)
    notify({
      type: ['holo', 'legend'].includes(rarity.value) ? 'success' : 'info',
      title: rarity.value === 'legend' ? '抽到傳說球員' : rarity.value === 'holo' ? '抽到閃卡球員' : rarity.value === 'rare' ? '抽到稀有球員' : '抽卡完成',
      message: `${cleanPlayerName(luckyPlayer)} 已加入收藏冊。`
    })
  } catch (err) {
    if (err.message === 'AUTH_REQUIRED') {
      error.value = '請先登入或註冊，才能把抽到的球員存進收藏冊。'
    } else if (err.message === 'SAVE_FAILED') {
      error.value = '卡牌儲存失敗，請確認後端 API 是否正常後再試一次。'
    } else {
      error.value = '請確認 Flask 是否啟動，以及 /api/get_player_pool 是否正常回傳資料。'
    }
  } finally {
    loading.value = false
    opening.value = false
    openingStep.value = 'idle'
  }
}

async function openPointPack(packType) {
  if (!auth?.token?.value) {
    error.value = '請先登入或註冊，才能使用收藏點數開包。'
    return
  }

  loading.value = true
  opening.value = true
  openingStep.value = 'shuffle'
  error.value = ''
  player.value = null
  cheerPlayerReady.value = false
  cheerVideoInput.value = ''
  imageMissing.value = false
  try {
    await delay(360)
    openingStep.value = 'scout'
    await delay(360)
    openingStep.value = 'reveal'
    const result = await cpblApi.buyPointPack(packType, auth.token.value)
    await delay(360)
    player.value = result.card
    drawKey.value += 1
    playCheerSong()
    if (auth.user) auth.user.value = result.user
    addPlayerToCollection(result.card)
    await auth.refreshCards?.()
    addRecentDraw(result.card)
    notify({
      type: ['holo', 'legend'].includes(playerRarity(result.card)) ? 'success' : 'info',
      title: packType === 'premium' ? '高級包開啟' : '標準包開啟',
      message: `花費 ${result.cost} 點，獲得 ${cleanPlayerName(result.card)}。`
    })
  } catch (err) {
    error.value = err?.message?.includes('不足')
      ? '收藏點數不足，可以先分解重複卡取得點數。'
      : '點數開包失敗，請確認後端 API 是否正常。'
  } finally {
    loading.value = false
    opening.value = false
    openingStep.value = 'idle'
  }
}

function delay(ms) {
  return new Promise(resolve => window.setTimeout(resolve, ms))
}

function playCheerSong() {
  cheerPlayerReady.value = false
  window.setTimeout(() => {
    if (cheerSong.value.hasVideo) cheerPlayerReady.value = true
  }, 30)
}

function addRecentDraw(card) {
  recentDraws.value = [
    {
      name: cleanPlayerName(card),
      team: card.team || '',
      rarity: playerRarity(card),
      drawnAt: Date.now()
    },
    ...recentDraws.value
  ].slice(0, 5)
}

function rollRarity(p) {
  const base = playerRarity(p)
  if (base === 'legend') return 'legend'
  if (base === 'holo') return 'holo'
  const value = Math.random()
  const legendRate = packMode.value === 'premium' ? 0.06 : 0.03
  const holoRate = packMode.value === 'premium' ? 0.14 : 0.07
  const rareRate = packMode.value === 'premium' ? 0.35 : 0.2
  if (value < legendRate) return 'legend'
  if (value < legendRate + holoRate) return 'holo'
  if (value < legendRate + holoRate + rareRate) return 'rare'
  return base
}

async function searchPlayer() {
  if (!keyword.value.trim()) {
    notify({ type: 'warning', title: '請輸入姓名', message: '輸入球員姓名後再搜尋。' })
    return
  }
  loading.value = true
  error.value = ''
  player.value = null
  cheerPlayerReady.value = false
  cheerVideoInput.value = ''
  imageMissing.value = false
  try {
    const players = await getPool()
    const found = players.find(p => (p.name || '').replace(/\*/g, '').includes(keyword.value.trim()))
    if (!found) {
      error.value = '找不到球員，請確認姓名是否正確，或先同步球員資料。'
      return
    }
    player.value = { ...found, rarity: playerRarity(found) }
    drawKey.value += 1
    imageMissing.value = false
    playCheerSong()
  } catch {
    error.value = '搜尋失敗，請確認球員 API 是否正常。'
  } finally {
    loading.value = false
  }
}

function saveCheerLink() {
  if (!player.value || !cheerVideoInput.value.trim()) {
    notify({ type: 'warning', title: '還沒有連結', message: '請先貼上 YouTube 連結或影片 ID。' })
    return
  }

  const saved = saveCheerOverride(player.value, cheerVideoInput.value)
  if (!saved) {
    notify({ type: 'error', title: '收錄失敗', message: '請確認連結或影片 ID 是否正確。' })
    return
  }

  cheerOverrideVersion.value += 1
  cheerVideoInput.value = ''
  playCheerSong()
  notify({ type: 'success', title: '應援曲已收錄', message: `${cleanName.value} 下次抽到會直接播放。` })
}
</script>
