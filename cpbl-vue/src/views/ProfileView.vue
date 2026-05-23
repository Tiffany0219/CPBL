<template>
  <div>
    <section class="section-header">
      <div>
        <p class="eyebrow">MY CLUBHOUSE</p>
        <h2>{{ auth?.user?.value?.username || '會員主頁' }}</h2>
        <p>查看卡牌、票夾、每日獎勵與最愛球隊設定。</p>
      </div>

      <div class="lineup-header-actions">
        <button class="btn-soft" type="button" :disabled="loading" @click="loadProfile">
          <i :class="loading ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-rotate'"></i>
          重新整理
        </button>

        <button class="btn-primary" type="button" :disabled="rewardLoading || profile?.summary?.daily_claimed" @click="claimDaily">
          <i class="fa-solid fa-gift"></i>
          {{ profile?.summary?.daily_claimed ? '今日已領取' : '領每日卡牌' }}
        </button>
      </div>
    </section>

    <StateBox v-if="loading" type="loading" message="正在整理你的會員資料..." />
    <StateBox v-else-if="error" type="error" title="讀取失敗" :message="error" />

    <template v-else>
      <section class="profile-hero-card">
        <div>
          <p class="eyebrow">FAVORITE TEAM</p>
          <h3>{{ auth?.user?.value?.favorite_team || '尚未設定最愛球隊' }}</h3>
          <p>設定後首頁會更容易看到你在意的球隊資訊。</p>
        </div>

        <select v-model="favoriteTeam" class="collection-filter" @change="saveFavoriteTeam">
          <option value="">尚未設定</option>
          <option v-for="team in teams" :key="team" :value="team">{{ team }}</option>
        </select>
      </section>

      <section class="collection-stats profile-stats">
        <article class="lineup-summary-card">
          <span>不同球員</span>
          <strong>{{ profile?.summary?.unique_cards || 0 }}</strong>
        </article>
        <article class="lineup-summary-card">
          <span>卡片總數</span>
          <strong>{{ profile?.summary?.total_cards || 0 }}</strong>
        </article>
        <article class="lineup-summary-card">
          <span>票夾紀錄</span>
          <strong>{{ profile?.summary?.ticket_count || 0 }}</strong>
        </article>
        <article class="lineup-summary-card">
          <span>最多收藏</span>
          <strong>{{ profile?.summary?.top_team || '-' }}</strong>
        </article>
        <article class="lineup-summary-card">
          <span>收藏點數</span>
          <strong>{{ profile?.summary?.card_points || 0 }}</strong>
        </article>
        <article class="lineup-summary-card">
          <span>連續領獎</span>
          <strong>{{ profile?.summary?.daily_streak || 0 }} 天</strong>
        </article>
      </section>

      <section class="daily-reward-card">
        <div>
          <p class="eyebrow">DAILY REWARD</p>
          <h3>{{ profile?.summary?.daily_claimed ? '今日已領取' : '今日可以領卡' }}</h3>
          <p>
            目前連續 {{ profile?.summary?.daily_streak || 0 }} 天，
            下一次領取是第 {{ profile?.summary?.next_daily_streak || 1 }} 天。
            <span v-if="profile?.summary?.next_daily_guarantee">下一領保底閃卡以上。</span>
          </p>
        </div>
        <button class="btn-primary" type="button" :disabled="rewardLoading || profile?.summary?.daily_claimed" @click="claimDaily">
          <i class="fa-solid fa-gift"></i>
          {{ profile?.summary?.daily_claimed ? '已領取' : '領每日卡牌' }}
        </button>
      </section>

      <section class="profile-grid">
        <article class="collection-panel">
          <div class="lineup-panel-head">
            <div>
              <p class="eyebrow">CARD RARITY</p>
              <h3>稀有度統計</h3>
            </div>
          </div>

          <div class="rarity-breakdown">
            <span class="rarity-pill common">一般 {{ rarityCount('common') }}</span>
            <span class="rarity-pill rare">稀有 {{ rarityCount('rare') }}</span>
            <span class="rarity-pill holo">閃卡 {{ rarityCount('holo') }}</span>
            <span class="rarity-pill legend">傳說 {{ rarityCount('legend') }}</span>
          </div>
        </article>

        <article class="collection-panel">
          <div class="lineup-panel-head">
            <div>
              <p class="eyebrow">LEADERBOARD</p>
              <h3>收藏排行榜</h3>
            </div>
          </div>

          <div class="profile-list">
            <div v-for="card in profile?.leaderboard || []" :key="card.name" class="profile-list-row">
              <span>{{ card.name }}</span>
              <strong>x{{ card.count }}</strong>
            </div>
            <StateBox v-if="!profile?.leaderboard?.length" title="尚無卡牌" message="去抽卡頁領一張球員卡吧。" />
          </div>
        </article>
      </section>

      <section class="collection-panel">
        <div class="lineup-panel-head">
          <div>
            <p class="eyebrow">RECENT CARDS</p>
            <h3>最近收藏</h3>
          </div>
        </div>

        <div class="profile-card-strip">
          <article v-for="card in profile?.recent_cards || []" :key="card.name" :class="['profile-mini-card', card.rarity]">
            <span>{{ rarityLabel(card.rarity) }}</span>
            <strong>{{ card.name }}</strong>
            <small>{{ card.team || '未知球隊' }} · x{{ card.count }}</small>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { inject, onMounted, ref } from 'vue'
import { cpblApi } from '../api/cpblApi'
import StateBox from '../components/StateBox.vue'
import { TEAMS, rarityLabel } from '../composables/usePlayerCollection'

const notify = inject('notify', () => {})
const auth = inject('auth', null)
const teams = TEAMS
const profile = ref(null)
const favoriteTeam = ref('')
const loading = ref(false)
const rewardLoading = ref(false)
const error = ref('')

function rarityCount(rarity) {
  return profile.value?.summary?.rarities?.[rarity] || 0
}

async function loadProfile() {
  if (!auth?.token?.value) return
  loading.value = true
  error.value = ''

  try {
    profile.value = await cpblApi.getProfile(auth.token.value)
    favoriteTeam.value = profile.value?.user?.favorite_team || ''
    if (profile.value?.user && auth.user) auth.user.value = profile.value.user
  } catch {
    error.value = '會員資料讀取失敗，請確認後端 API 是否正常。'
  } finally {
    loading.value = false
  }
}

async function saveFavoriteTeam() {
  try {
    const result = await cpblApi.updateMe({ favorite_team: favoriteTeam.value }, auth.token.value)
    if (auth.user) auth.user.value = result.user
    await loadProfile()
    notify({ type: 'success', title: '已更新最愛球隊', message: favoriteTeam.value || '已清除最愛球隊。' })
  } catch {
    notify({ type: 'error', title: '更新失敗', message: '最愛球隊暫時沒有儲存成功。' })
  }
}

async function claimDaily() {
  rewardLoading.value = true
  try {
    const result = await cpblApi.claimDailyReward(auth.token.value)
    if (auth.user) auth.user.value = result.user
    await auth.refreshCards?.()
    await loadProfile()
    notify({
      type: 'success',
      title: result.guaranteed_bonus ? '保底閃卡獎勵' : '每日獎勵已領取',
      message: `連續 ${result.streak} 天，獲得 ${result.card.name}。`
    })
  } catch (err) {
    notify({ type: 'warning', title: '無法領取', message: err?.message?.includes('已經') ? '今天已經領過囉。' : '請確認球員池或後端 API。' })
  } finally {
    rewardLoading.value = false
  }
}

onMounted(loadProfile)
</script>
