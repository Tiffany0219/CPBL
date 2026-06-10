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

        <button class="btn-soft" type="button" :disabled="duplicateCount === 0 || !auth?.token?.value" @click="convertDuplicates">
          <i class="fa-solid fa-coins"></i>
          重複卡換點數
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

      <article class="lineup-summary-card">
        <span>重複卡 / 點數</span>
        <strong>{{ duplicateCount }} / {{ cardPoints }}</strong>
      </article>
    </section>

    <section class="collection-panel collection-progress-panel">
      <div class="lineup-panel-head">
        <div>
          <p class="eyebrow">CARD INDEX</p>
          <h3>圖鑑進度</h3>
        </div>
        <span>{{ collectionCompletion }}%</span>
      </div>

      <div class="collection-progress-grid">
        <article v-for="item in teamProgress" :key="item.team" class="collection-progress-row">
          <div class="progress-row-head">
            <strong>{{ item.team }}</strong>
            <span>{{ item.owned }}/{{ item.total }}</span>
          </div>
          <div class="progress-track">
            <i :style="{ width: `${item.percent}%`, background: teamColor(item.team) }"></i>
          </div>
        </article>
      </div>

      <div class="rarity-progress-strip">
        <span v-for="item in rarityProgress" :key="item.value" :class="['rarity-pill', item.value]">
          {{ item.label }} {{ item.count }}
        </span>
      </div>
    </section>

    <!-- Tab 切換器 -->
    <div class="view-toggle collection-tab-toggle" style="margin: 24px 0 16px;">
      <button :class="{ active: activeTab === 'album' }" type="button" @click="activeTab = 'album'">
        <i class="fa-solid fa-book-open"></i>
        我的收藏卡冊
      </button>
      <button :class="{ active: activeTab === 'fusion' }" type="button" @click="activeTab = 'fusion'">
        <i class="fa-solid fa-wand-magic-sparkles"></i>
        卡牌熔煉爐
      </button>
    </div>

    <section v-if="activeTab === 'album'" class="collection-panel collection-page-panel">
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

        <select v-model="rarityFilter" class="collection-filter">
          <option value="">全部稀有度</option>
          <option v-for="option in rarityOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>

        <select v-model="positionFilter" class="collection-filter">
          <option value="">全部位置</option>
          <option v-for="position in positionOptions" :key="position" :value="position">{{ position }}</option>
        </select>

        <select v-model="sortMode" class="collection-filter">
          <option v-for="option in sortOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
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
          @keydown.enter="selectedPlayer = player"
          tabindex="0"
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
            <small>{{ cardSerial(player) }}</small>
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

    <!-- 卡牌熔煉爐面版 -->
    <section v-else-if="activeTab === 'fusion'" class="collection-panel collection-page-panel">
      <div class="lineup-panel-head">
        <div>
          <p class="eyebrow">CARD FUSION</p>
          <h3>卡牌熔煉爐</h3>
        </div>
        <span>放入 {{ fusionSlotsCount }} 張「一般」卡牌進行高級熔煉</span>
      </div>

      <div class="fusion-console">
        <!-- 熔煉模式選擇 -->
        <div class="fusion-mode-selector">
          <button
            type="button"
            :class="{ active: fusionSlotsCount === 3 }"
            :disabled="isFusing"
            @click="setFusionSlotsCount(3)"
          >
            <strong>3 卡熔煉 (耗費少)</strong>
            <span>機率：80% 稀有 / 15% 閃卡 / 5% 傳說</span>
          </button>
          <button
            type="button"
            :class="{ active: fusionSlotsCount === 5 }"
            :disabled="isFusing"
            @click="setFusionSlotsCount(5)"
          >
            <strong>5 卡熔煉 (機率高)</strong>
            <span>機率：65% 稀有 / 25% 閃卡 / 10% 傳說</span>
          </button>
        </div>

        <!-- 熔煉插槽 -->
        <div class="fusion-slots-container">
          <div
            v-for="index in fusionSlotsCount"
            :key="index"
            :class="['fusion-slot-box', { filled: fusionMaterials[index - 1] }]"
            @click="removeFromFusion(index - 1)"
          >
            <template v-if="fusionMaterials[index - 1]">
              <div class="fusion-slot-avatar">
                <img
                  v-if="!failedImages[cleanName(fusionMaterials[index - 1])]"
                  :src="playerImage(fusionMaterials[index - 1])"
                  @error="markImageFailed(fusionMaterials[index - 1])"
                />
                <span v-else>{{ initials(fusionMaterials[index - 1]) }}</span>
              </div>
              <strong class="fusion-slot-name">{{ cleanName(fusionMaterials[index - 1]) }}</strong>
              <div class="fusion-slot-remove"><i class="fa-solid fa-xmark"></i></div>
            </template>
            <template v-else>
              <div class="fusion-slot-empty">
                <i class="fa-solid fa-plus"></i>
                <span>放入一般卡</span>
              </div>
            </template>
          </div>
        </div>

        <!-- 開始熔煉按鈕 -->
        <div class="fusion-actions">
          <button
            class="btn-primary btn-large"
            type="button"
            :disabled="fusionMaterials.length < fusionSlotsCount || isFusing"
            @click="startFusion"
          >
            <i :class="isFusing ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-wand-magic-sparkles'"></i>
            {{ isFusing ? '熔煉中...' : '開始熔煉' }}
          </button>
        </div>
      </div>

      <!-- 可選擇放入的普通卡清單 -->
      <div class="fusion-materials-panel">
        <div class="lineup-panel-head">
          <div>
            <p class="eyebrow">COMMON CARDS</p>
            <h4>可選材料卡片（僅限「一般」稀有度）</h4>
          </div>
          <span>可用球員：{{ commonCards.length }} 位</span>
        </div>

        <StateBox
          v-if="commonCards.length === 0"
          title="沒有可用的材料卡片"
          message="熔煉需要消耗您擁有的「一般 (Common)」球員卡，可以先去抽卡獲得。"
        />

        <div v-else class="collection-page-grid fusion-grid-small">
          <article
            v-for="player in commonCards"
            :key="cleanName(player)"
            :class="['collection-card-large common', { 'disabled': getAvailableCount(player) <= 0 }]"
            :style="{ '--team-color': teamColor(player.team) }"
            @click="addToFusion(player)"
          >
            <div class="collection-card-top">
              <span>{{ player.team || '未知球隊' }}</span>
              <strong>可用: {{ getAvailableCount(player) }} / {{ player.count || 1 }}</strong>
            </div>

            <div class="collection-card-avatar" style="height: 100px;">
              <img
                v-if="!failedImages[cleanName(player)]"
                :src="playerImage(player)"
                :alt="cleanName(player)"
                @error="markImageFailed(player)"
              />
              <span v-else>{{ initials(player) }}</span>
            </div>

            <div class="collection-card-body" style="padding: 10px;">
              <h3 style="font-size: 16px; margin: 0;">{{ cleanName(player) }}</h3>
              <p style="font-size: 11px; margin: 2px 0 0;">{{ player.position || '未知位置' }}</p>
            </div>
            
            <div class="fusion-add-overlay" v-if="getAvailableCount(player) > 0">
              <i class="fa-solid fa-plus"></i>
              <span>放入插槽</span>
            </div>
          </article>
        </div>
      </div>
    </section>

    <!-- 熔煉融合動畫與結果 Modal -->
    <div v-if="showFusionModal" class="modal" style="display:block;">
      <div class="modal-content card-detail-modal legend" style="max-width: 500px; text-align: center; overflow: hidden; padding-bottom: 28px;">
        <button class="modal-close" type="button" v-if="!animationRunning" @click="showFusionModal = false">&times;</button>
        
        <!-- 動態融合階段 -->
        <div v-if="animationRunning" class="fusion-animation-stage">
          <div class="fusion-swirl-container">
            <div class="fusion-sparkle-core"><i class="fa-solid fa-wand-magic-sparkles"></i></div>
            <div class="fusion-particle-orbit">
              <div v-for="n in 8" :key="n" :class="'fusion-dot dot-' + n"></div>
            </div>
          </div>
          <h3 class="fusion-pulse-text">卡牌熔煉中...</h3>
          <p style="color: #64748b;">正在將普通卡牌提煉為更高稀有度卡片</p>
        </div>

        <!-- 熔煉成功結果揭曉 -->
        <div v-else-if="fusedResultCard" class="fusion-result-stage">
          <p class="eyebrow" style="color: #ea580c; font-weight: 800; font-size: 12px; letter-spacing: 2px;">FUSION SUCCESS</p>
          <h2 style="color: #0b1f33; font-weight: 900; margin: 5px 0 24px; font-size: 32px;">熔煉成功！</h2>
          
          <div class="gacha-result-shell" style="display: flex; justify-content: center; margin-bottom: 24px;">
            <article
              :class="['player-card-site', fusedResultCard.rarity || 'common', { 'is-full-card': isFusedResultFullCard }]"
              :style="{ '--team-color': teamColor(fusedResultCard.team), margin: '0 auto' }"
            >
              <div class="holo-layer" aria-hidden="true"></div>
              <div class="card-inner-frame" aria-hidden="true"></div>
              <div class="rarity-medallion">
                <strong>{{ rarityLabel(fusedResultCard.rarity) }}</strong>
              </div>
              <div class="player-card-top">
                <span>NEW FUSION</span>
                <strong>{{ rarityLabel(fusedResultCard.rarity) }}</strong>
              </div>
              <div class="player-photo-wrap">
                <img
                  v-if="!failedImages[cleanName(fusedResultCard)]"
                  :src="fusedResultImage"
                  @error="handleFusionImageError"
                />
                <div v-else class="player-photo-fallback">
                  {{ initials(fusedResultCard) }}
                </div>
              </div>
              <div class="player-card-info">
                <h3>{{ cleanName(fusedResultCard) }}</h3>
                <p>{{ fusedResultCard.team || '未知球隊' }} · {{ fusedResultCard.position || '未知位置' }}</p>
              </div>
              <div class="player-card-stats">
                <span>
                  <small>TEAM</small>
                  <b>{{ fusedResultCard.team || '未知' }}</b>
                </span>
                <span>
                  <small>POS</small>
                  <b>{{ fusedResultCard.position || '未知' }}</b>
                </span>
                <span>
                  <small>TYPE</small>
                  <b>{{ rarityLabel(fusedResultCard.rarity) }}</b>
                </span>
              </div>
              <div class="player-card-desc">
                {{ fusedResultCard.description || '在熔煉爐中誕生的全新卡牌！' }}
              </div>
            </article>
          </div>

          <div style="display: flex; justify-content: center; gap: 12px;">
            <button class="btn-primary" type="button" @click="showFusionModal = false" style="margin: 0;">
              收進卡冊
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="selectedPlayer" class="modal">
      <div
        :class="['modal-content', 'card-detail-modal', selectedPlayer.rarity || 'common']"
        :style="{ '--team-color': teamColor(selectedPlayer.team) }"
      >
        <button class="modal-close" type="button" @click="selectedPlayer = null">&times;</button>
        <p class="eyebrow">PLAYER CARD DETAIL</p>
        <div class="card-detail-head">
          <div class="card-detail-avatar">
            <img
              v-if="!failedImages[cleanName(selectedPlayer)]"
              :src="playerImage(selectedPlayer)"
              :alt="cleanName(selectedPlayer)"
              @error="markImageFailed(selectedPlayer)"
            />
            <span v-else>{{ initials(selectedPlayer) }}</span>
          </div>
          <div>
            <div class="card-detail-tags">
              <span :class="['rarity-pill', selectedPlayer.rarity || 'common']">{{ rarityLabel(selectedPlayer.rarity) }}</span>
              <b>{{ cardSerial(selectedPlayer) }}</b>
            </div>
            <h2>{{ cleanName(selectedPlayer) }}</h2>
            <p>{{ selectedPlayer.team || '未知球隊' }} · {{ selectedPlayer.position || '未知位置' }}</p>
          </div>
        </div>
        <p class="card-detail-desc">{{ selectedPlayer.description || '這位球員已加入你的收藏冊，之後可以排進我的打線。' }}</p>

        <div class="card-detail-grid">
          <div>
            <span>持有張數</span>
            <strong>x{{ selectedPlayer.count || 1 }}</strong>
          </div>
          <div>
            <span>可換點數</span>
            <strong>{{ duplicatePoints(selectedPlayer) }}</strong>
          </div>
          <div>
            <span>球隊</span>
            <strong>{{ selectedPlayer.team || '未知' }}</strong>
          </div>
          <div>
            <span>守位</span>
            <strong>{{ selectedPlayer.position || '未知' }}</strong>
          </div>
          <div>
            <span>稀有度</span>
            <strong>{{ rarityLabel(selectedPlayer.rarity) }}</strong>
          </div>
        </div>

        <div class="card-detail-actions">
          <button class="btn-soft" type="button" @click="copyPlayerName(selectedPlayer)">
            <i class="fa-solid fa-copy"></i>
            複製姓名
          </button>
          <button class="btn-soft" type="button" :disabled="(selectedPlayer.count || 1) <= 1 || !auth?.token?.value" @click="convertOneDuplicate(selectedPlayer)">
            <i class="fa-solid fa-coins"></i>
            分解重複卡
          </button>
          <button class="btn-primary" type="button" @click="selectedPlayer = null">
            <i class="fa-solid fa-check"></i>
            收進卡冊
          </button>
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
  teamColor,
  readCollectionMap
} from '../composables/usePlayerCollection'

const ASSET_BASE = API_BASE.replace(/\/api$/, '')
const notify = inject('notify', () => {})
const confirmAction = inject('confirmAction', async () => false)
const auth = inject('auth', null)
const collection = ref([])
const playerPool = ref([])
const keyword = ref('')
const teamFilter = ref('')
const rarityFilter = ref('')
const positionFilter = ref('')
const sortMode = ref('rarity')
const failedImages = ref({})
const selectedPlayer = ref(null)
const teams = TEAMS

const activeTab = ref('album')
const fusionSlotsCount = ref(3)
const fusionMaterials = ref([])
const isFusing = ref(false)
const showFusionModal = ref(false)
const animationRunning = ref(false)
const fusedResultCard = ref(null)
const triedNormalFusionImage = ref(false)
const fusedImageOverride = ref('')

const isFusedResultFullCard = computed(() => {
  return fusedResultCard.value && !triedNormalFusionImage.value
})

const fusedResultImage = computed(() => {
  if (!fusedResultCard.value) return ''
  if (fusedImageOverride.value) return fusedImageOverride.value
  const name = cleanName(fusedResultCard.value)
  if (isFusedResultFullCard.value) {
    return `${ASSET_BASE}/static/image/players/${encodeURIComponent(name)}_card.png`
  }
  return playerImage(fusedResultCard.value)
})

function handleFusionImageError() {
  if (isFusedResultFullCard.value && !triedNormalFusionImage.value) {
    triedNormalFusionImage.value = true
    fusedImageOverride.value = playerImage(fusedResultCard.value)
  } else if (fusedResultCard.value) {
    markImageFailed(fusedResultCard.value)
  }
}

const commonCards = computed(() => {
  return collection.value.filter(player => (player.rarity || 'common') === 'common')
})

function setFusionSlotsCount(count) {
  fusionSlotsCount.value = count
  fusionMaterials.value = []
}

function addToFusion(player) {
  if (isFusing.value) return
  const currentCount = fusionMaterials.value.filter(p => cleanName(p) === cleanName(player)).length
  const ownedCount = player.count || 1
  if (currentCount >= ownedCount) {
    notify({ type: 'warning', title: '數量不足', message: `您持有的 ${cleanName(player)} 已全部放入插槽。` })
    return
  }
  if (fusionMaterials.value.length >= fusionSlotsCount.value) {
    notify({ type: 'warning', title: '插槽已滿', message: `熔煉插槽目前限制為 ${fusionSlotsCount.value} 張。` })
    return
  }
  fusionMaterials.value.push(player)
}

function removeFromFusion(index) {
  if (isFusing.value) return
  if (index >= 0 && index < fusionMaterials.value.length) {
    fusionMaterials.value.splice(index, 1)
  }
}

function getAvailableCount(player) {
  const currentCount = fusionMaterials.value.filter(p => cleanName(p) === cleanName(player)).length
  return Math.max(0, (player.count || 1) - currentCount)
}

async function startFusion() {
  if (fusionMaterials.value.length < fusionSlotsCount.value) {
    notify({ type: 'warning', title: '插槽未滿', message: `請放滿 ${fusionSlotsCount.value} 張一般球員卡再進行熔煉。` })
    return
  }

  isFusing.value = true
  showFusionModal.value = true
  animationRunning.value = true
  fusedResultCard.value = null
  triedNormalFusionImage.value = false
  fusedImageOverride.value = ''

  const materials = fusionMaterials.value.map(p => cleanName(p))

  try {
    if (auth?.token?.value) {
      const result = await cpblApi.fuseUserCards(materials, fusionSlotsCount.value, auth.token.value)
      await delay(1800)
      animationRunning.value = false
      fusedResultCard.value = result.new_card
      if (auth.user) auth.user.value = result.user
      saveCollectionMap(collectionListToMap(result.cards || []))
      collection.value = getCollectionList()
    } else {
      await delay(1800)
      if (playerPool.value.length === 0) {
        throw new Error('球員池資料尚未載入，請先回首頁或重新整理更新。')
      }

      const roll = Math.random()
      let rarity = 'rare'
      if (fusionSlotsCount.value === 5) {
        if (roll < 0.10) rarity = 'legend'
        else if (roll < 0.35) rarity = 'holo'
      } else {
        if (roll < 0.05) rarity = 'legend'
        else if (roll < 0.20) rarity = 'holo'
      }

      const usable = playerPool.value.filter(p => !p.team?.includes('二軍'))
      const pool = usable.length ? usable : playerPool.value
      const luckyPlayer = pool[Math.floor(Math.random() * pool.length)]
      
      const newCard = {
        name: cleanPlayerName(luckyPlayer),
        team: luckyPlayer.team || '',
        position: luckyPlayer.position || '',
        description: luckyPlayer.description || '在熔煉爐中誕生的全新卡牌！',
        rarity: newCardRarity(luckyPlayer, rarity),
        count: 1
      }

      const collectionMap = readCollectionMap()
      materials.forEach(name => {
        if (collectionMap[name]) {
          collectionMap[name].count = (collectionMap[name].count || 1) - 1
          if (collectionMap[name].count <= 0) {
            delete collectionMap[name]
          }
        }
      })

      const existing = collectionMap[newCard.name]
      if (existing) {
        collectionMap[newCard.name].count = (existing.count || 1) + 1
      } else {
        collectionMap[newCard.name] = newCard
      }

      saveCollectionMap(collectionMap)
      collection.value = getCollectionList()
      
      animationRunning.value = false
      fusedResultCard.value = newCard
    }

    notify({ type: 'success', title: '熔煉完成', message: `獲得了 ${rarityLabel(fusedResultCard.value.rarity)}卡：${cleanName(fusedResultCard.value)}！` })
    fusionMaterials.value = []
  } catch (err) {
    showFusionModal.value = false
    notify({ type: 'error', title: '熔煉失敗', message: err.message || '發生錯誤，請稍後再試。' })
  } finally {
    isFusing.value = false
  }
}

function newCardRarity(p, baseRarity) {
  const name = cleanPlayerName(p)
  if (name === '頌恩') return 'legend'
  return baseRarity
}

function delay(ms) {
  return new Promise(resolve => window.setTimeout(resolve, ms))
}

const rarityRank = { legend: 4, holo: 3, rare: 2, common: 1 }
const rarityOptions = [
  { value: 'legend', label: '傳說' },
  { value: 'holo', label: '閃卡' },
  { value: 'rare', label: '稀有' },
  { value: 'common', label: '一般' }
]
const sortOptions = [
  { value: 'rarity', label: '稀有度排序' },
  { value: 'count', label: '持有張數排序' },
  { value: 'team', label: '球隊排序' },
  { value: 'name', label: '姓名排序' }
]

const filteredCollection = computed(() => {
  const text = keyword.value.trim().toLowerCase()

  return collection.value.filter(player => {
    const content = `${cleanName(player)} ${player.team || ''} ${player.position || ''}`.toLowerCase()
    const matchesText = !text || content.includes(text)
    const matchesTeam = !teamFilter.value || player.team === teamFilter.value
    const matchesRarity = !rarityFilter.value || (player.rarity || 'common') === rarityFilter.value
    const matchesPosition = !positionFilter.value || player.position === positionFilter.value

    return matchesText && matchesTeam && matchesRarity && matchesPosition
  }).sort(sortPlayers)
})

const totalCards = computed(() => collection.value.reduce((sum, player) => sum + Number(player.count || 1), 0))
const ownedTeams = computed(() => new Set(collection.value.map(player => player.team).filter(Boolean)).size)
const duplicateCount = computed(() => collection.value.reduce((sum, player) => sum + Math.max(0, Number(player.count || 1) - 1), 0))
const cardPoints = computed(() => auth?.user?.value?.card_points || 0)
const positionOptions = computed(() => [...new Set(collection.value.map(player => player.position).filter(Boolean))]
  .sort((a, b) => a.localeCompare(b, 'zh-Hant')))
const topTeam = computed(() => {
  const counts = {}
  collection.value.forEach(player => {
    const team = player.team || '未知'
    counts[team] = (counts[team] || 0) + Number(player.count || 1)
  })

  const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]
  return top ? top[0] : '-'
})
const teamProgress = computed(() => teams.map(team => {
  const owned = new Set(
    collection.value
      .filter(player => player.team === team)
      .map(player => cleanName(player))
  ).size
  const totalFromPool = new Set(
    playerPool.value
      .filter(player => player.team === team && !String(player.team || '').includes('二軍'))
      .map(player => cleanPlayerName(player))
  ).size
  const total = Math.max(totalFromPool, owned, 1)
  return {
    team,
    owned,
    total,
    percent: Math.round((owned / total) * 100)
  }
}))
const collectionCompletion = computed(() => {
  const total = teamProgress.value.reduce((sum, item) => sum + item.total, 0)
  const owned = teamProgress.value.reduce((sum, item) => sum + item.owned, 0)
  return total ? Math.round((owned / total) * 100) : 0
})
const rarityProgress = computed(() => rarityOptions.map(option => ({
  ...option,
  count: collection.value.filter(player => (player.rarity || 'common') === option.value).length
})))

function cleanName(player) {
  return cleanPlayerName(player)
}

function initials(player) {
  return playerInitials(player)
}

function playerImage(player) {
  return `${ASSET_BASE}/static/image/players/${encodeURIComponent(cleanName(player))}.png`
}

function cardSerial(player) {
  const base = Array.from(cleanName(player)).reduce((sum, char) => sum + char.charCodeAt(0), 0)
  return `CPBL-${String(base % 9999).padStart(4, '0')}`
}

function rarityPointValue(rarity) {
  return {
    common: 6,
    rare: 12,
    holo: 28,
    legend: 60
  }[rarity || 'common'] || 6
}

function duplicatePoints(player) {
  return Math.max(0, Number(player.count || 1) - 1) * rarityPointValue(player.rarity)
}

function sortPlayers(a, b) {
  if (sortMode.value === 'count') {
    return Number(b.count || 1) - Number(a.count || 1) || cleanName(a).localeCompare(cleanName(b), 'zh-Hant')
  }
  if (sortMode.value === 'team') {
    return (a.team || '').localeCompare(b.team || '', 'zh-Hant') || cleanName(a).localeCompare(cleanName(b), 'zh-Hant')
  }
  if (sortMode.value === 'name') {
    return cleanName(a).localeCompare(cleanName(b), 'zh-Hant')
  }

  return (rarityRank[b.rarity || 'common'] || 0) - (rarityRank[a.rarity || 'common'] || 0)
    || Number(b.count || 1) - Number(a.count || 1)
    || cleanName(a).localeCompare(cleanName(b), 'zh-Hant')
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

async function loadPlayerPool() {
  try {
    const players = await cpblApi.getPlayerPool()
    playerPool.value = Array.isArray(players) ? players : []
  } catch {
    playerPool.value = []
  }
}

async function removePlayer(player) {
  const confirmed = await confirmAction({
    title: '移除球員卡',
    message: `確定要移除 ${cleanName(player)} 嗎？這張卡會從收藏冊消失。`,
    confirmText: '移除',
    danger: true
  })
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
  const confirmed = await confirmAction({
    title: '清空收藏冊',
    message: '確定要清空整本球員收藏冊嗎？這個動作無法復原。',
    confirmText: '清空',
    danger: true
  })
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

async function convertDuplicates() {
  if (!auth?.token?.value) {
    notify({ type: 'info', title: '請先登入', message: '重複卡換點數需要同步到會員帳號。' })
    return
  }

  const confirmed = await confirmAction({
    title: '重複卡換點數',
    message: `將 ${duplicateCount.value} 張重複卡分解成收藏點數，每位球員會保留 1 張。`,
    confirmText: '換成點數',
    icon: 'fa-solid fa-coins'
  })
  if (!confirmed) return

  try {
    const result = await cpblApi.convertDuplicateCards(auth.token.value)
    if (auth.user) auth.user.value = result.user
    saveCollectionMap(collectionListToMap(result.cards || []))
    collection.value = getCollectionList()
    notify({ type: 'success', title: '已兌換點數', message: `分解 ${result.converted} 張，獲得 ${result.points} 點。` })
  } catch (err) {
    notify({ type: 'warning', title: '沒有可分解卡', message: err?.message?.includes('重複') ? '目前沒有可換點數的重複卡。' : '兌換暫時失敗。' })
  }
}

async function convertOneDuplicate(player) {
  if (!auth?.token?.value || Number(player.count || 1) <= 1) return

  const confirmed = await confirmAction({
    title: '分解重複卡',
    message: `分解 1 張 ${cleanName(player)} 的重複卡，保留至少 1 張在收藏冊。`,
    confirmText: '分解',
    icon: 'fa-solid fa-coins'
  })
  if (!confirmed) return

  try {
    const result = await cpblApi.convertUserCard(cleanName(player), 1, auth.token.value)
    if (auth.user) auth.user.value = result.user
    await loadCollection()
    selectedPlayer.value = result.card
    notify({ type: 'success', title: '已獲得點數', message: `獲得 ${result.points} 點收藏點數。` })
  } catch {
    notify({ type: 'warning', title: '分解失敗', message: '這張卡目前沒有重複卡可分解。' })
  }
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

onMounted(() => {
  loadCollection()
  loadPlayerPool()
})
</script>

<style scoped>
.collection-tab-toggle {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.fusion-console {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 800px;
  margin: 0 auto;
  padding: 24px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 20px;
}

.fusion-mode-selector {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.fusion-mode-selector button {
  padding: 16px;
  background: #111e2e;
  border: 2px solid #1e293b;
  border-radius: 16px;
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  transition: all 0.25s ease;
}

.fusion-mode-selector button.active {
  border-color: #38bdf8;
  background: #0f2b48;
  color: #ffffff;
  box-shadow: 0 0 20px rgba(56, 189, 248, 0.15);
}

.fusion-mode-selector button strong {
  font-size: 16px;
  font-weight: 900;
}

.fusion-mode-selector button span {
  font-size: 12px;
  opacity: 0.8;
}

.fusion-slots-container {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  min-height: 180px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 16px;
}

.fusion-slot-box {
  width: 110px;
  height: 150px;
  background: rgba(255, 255, 255, 0.03);
  border: 2px dashed #475569;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  transition: all 0.2s ease;
  overflow: hidden;
}

.fusion-slot-box.filled {
  border: 2px solid #38bdf8;
  background: #0b1f33;
}

.fusion-slot-box:hover {
  transform: translateY(-2px);
  border-color: #38bdf8;
}

.fusion-slot-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #64748b;
}

.fusion-slot-empty i {
  font-size: 20px;
}

.fusion-slot-empty span {
  font-size: 11px;
  font-weight: 800;
}

.fusion-slot-avatar {
  width: 70px;
  height: 70px;
  border-radius: 50%;
  overflow: hidden;
  background: #edf2f7;
  display: grid;
  place-items: center;
  margin-bottom: 8px;
}

.fusion-slot-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.fusion-slot-avatar span {
  font-size: 20px;
  font-weight: 900;
  color: #1e293b;
}

.fusion-slot-name {
  font-size: 13px;
  font-weight: 900;
  color: #f1f5f9;
}

.fusion-slot-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: rgba(220, 38, 38, 0.8);
  color: #ffffff;
  display: grid;
  place-items: center;
  font-size: 9px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.fusion-slot-box.filled:hover .fusion-slot-remove {
  opacity: 1;
}

.fusion-actions {
  display: flex;
  justify-content: center;
}

.fusion-actions button {
  width: 100%;
  max-width: 320px;
  font-size: 18px;
  padding: 12px 24px;
  border-radius: 999px;
}

.fusion-grid-small {
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)) !important;
  gap: 12px !important;
}

.fusion-grid-small .collection-card-large {
  position: relative;
  overflow: hidden;
}

.fusion-grid-small .collection-card-large.disabled {
  opacity: 0.4;
  cursor: not-allowed;
  pointer-events: none;
}

.fusion-add-overlay {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.85);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #38bdf8;
  opacity: 0;
  transition: opacity 0.2s ease;
  cursor: pointer;
}

.collection-card-large:hover .fusion-add-overlay {
  opacity: 1;
}

.fusion-add-overlay i {
  font-size: 24px;
}

.fusion-add-overlay span {
  font-size: 12px;
  font-weight: 900;
}

/* Fusion Animation Styles */
.fusion-animation-stage {
  padding: 40px 20px;
}

.fusion-swirl-container {
  width: 120px;
  height: 120px;
  margin: 0 auto 24px;
  position: relative;
  display: grid;
  place-items: center;
}

.fusion-sparkle-core {
  font-size: 42px;
  color: #f59e0b;
  animation: pulse-core 1.2s ease-in-out infinite alternate;
}

.fusion-particle-orbit {
  position: absolute;
  inset: 0;
  animation: rotate-orbit 2.2s linear infinite;
}

.fusion-dot {
  position: absolute;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #38bdf8;
}

.dot-1 { top: 0; left: 50%; transform: translateX(-50%); background: #f43f5e; }
.dot-2 { top: 14%; left: 85%; background: #38bdf8; }
.dot-3 { top: 50%; left: 100%; transform: translateY(-50%); background: #f59e0b; }
.dot-4 { top: 85%; left: 85%; background: #10b981; }
.dot-5 { top: 100%; left: 50%; transform: translateX(-50%); background: #a855f7; }
.dot-6 { top: 85%; left: 14%; background: #06b6d4; }
.dot-7 { top: 50%; left: 0; transform: translateY(-50%); background: #ec4899; }
.dot-8 { top: 14%; left: 14%; background: #eab308; }

.fusion-pulse-text {
  font-size: 24px;
  font-weight: 900;
  color: #0b1f33;
  animation: pulse-text 1s ease-in-out infinite alternate;
}

@keyframes pulse-core {
  0% { transform: scale(0.8); opacity: 0.8; }
  100% { transform: scale(1.3); opacity: 1; filter: drop-shadow(0 0 12px #f59e0b); }
}

@keyframes rotate-orbit {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes pulse-text {
  0% { opacity: 0.6; }
  100% { opacity: 1; }
}
</style>
