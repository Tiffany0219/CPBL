<template>
  <div v-if="show" class="modal" style="display:block;">
    <div class="modal-content game-detail-modal">
      <button class="modal-close" type="button" aria-label="關閉比賽詳情" @click="$emit('close')">
        <i class="fa-solid fa-xmark"></i>
      </button>

      <StateBox
        v-if="loading"
        type="loading"
        message="載入比賽詳細資料中..."
      />

      <div v-else-if="error" class="empty-state error-state">
        <i class="fa-solid fa-triangle-exclamation"></i>
        <h3>資料載入失敗</h3>
        <p>{{ error }}</p>
      </div>

      <div v-else-if="detail" class="detail-content">
        <section class="detail-hero-panel">
          <div class="detail-hero-copy">
            <p class="eyebrow">GAME DETAIL</p>
            <h2>{{ detailTitle }}</h2>
            <p>逐局比分、R-H-E 統計、投手與打擊數據</p>
          </div>

          <div class="detail-matchup-board">
            <div :class="['detail-team-block', { winner: winnerSide === 'away' }]">
              <span>AWAY</span>
              <img :src="teamLogo(detail.away_team)" :alt="detail.away_team" />
              <strong>{{ detail.away_team }}</strong>
            </div>

            <div class="detail-score-board">
              <span>FINAL</span>
              <div>
                <b>{{ awayRuns }}</b>
                <em>:</em>
                <b>{{ homeRuns }}</b>
              </div>
              <small>{{ winnerText }}</small>
            </div>

            <div :class="['detail-team-block', 'right', { winner: winnerSide === 'home' }]">
              <span>HOME</span>
              <img :src="teamLogo(detail.home_team)" :alt="detail.home_team" />
              <strong>{{ detail.home_team }}</strong>
            </div>
          </div>

          <div class="detail-meta-grid">
            <article>
              <i class="fa-solid fa-baseball"></i>
              <span>先發投手</span>
              <strong>{{ startersText }}</strong>
              <small>{{ starterMeta }}</small>
            </article>

            <article class="mvp">
              <i class="fa-solid fa-star"></i>
              <span>單場 MVP</span>
              <strong>{{ mvpText }}</strong>
              <small>{{ mvpMeta }}</small>
            </article>

            <article>
              <i class="fa-solid fa-trophy"></i>
              <span>勝敗投</span>
              <strong>{{ decisionText }}</strong>
              <small>{{ saveText }}</small>
            </article>
          </div>
        </section>

        <!-- 逐局比分 -->
        <section class="detail-section">
          <div class="detail-section-title">
            <div>
              <p class="eyebrow">LINE SCORE</p>
              <h3>逐局比分</h3>
            </div>
            <div class="rhe-pills">
              <span>R {{ awayRuns }} - {{ homeRuns }}</span>
              <span>H {{ detail.away_rhe?.[1] ?? '0' }} - {{ detail.home_rhe?.[1] ?? '0' }}</span>
              <span>E {{ detail.away_rhe?.[2] ?? '0' }} - {{ detail.home_rhe?.[2] ?? '0' }}</span>
            </div>
          </div>

          <div class="table-scroll">
            <table class="detail-table line-score-table">
              <thead>
                <tr>
                  <th>TEAM</th>
                  <th v-for="i in totalInnings" :key="'inning-' + i">
                    {{ i }}
                  </th>
                  <th>R</th>
                  <th>H</th>
                  <th>E</th>
                </tr>
              </thead>

              <tbody>
                <tr>
                  <td class="team-cell"><b>{{ detail.away_team }}</b></td>

                  <td v-for="i in totalInnings" :key="'away-line-' + i">
                    {{ detail.away_line?.[i - 1] ?? '' }}
                  </td>

                  <td class="stat-cell strong-score">{{ detail.away_rhe?.[0] ?? '0' }}</td>
                  <td class="stat-cell">{{ detail.away_rhe?.[1] ?? '0' }}</td>
                  <td class="stat-cell">{{ detail.away_rhe?.[2] ?? '0' }}</td>
                </tr>

                <tr>
                  <td class="team-cell"><b>{{ detail.home_team }}</b></td>

                  <td v-for="i in totalInnings" :key="'home-line-' + i">
                    {{ detail.home_line?.[i - 1] ?? '' }}
                  </td>

                  <td class="stat-cell strong-score">{{ detail.home_rhe?.[0] ?? '0' }}</td>
                  <td class="stat-cell">{{ detail.home_rhe?.[1] ?? '0' }}</td>
                  <td class="stat-cell">{{ detail.home_rhe?.[2] ?? '0' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- 打擊數據 -->
        <section class="batting-grid">
          <div class="batting-card">
            <div class="batting-card-head away-head">
              <span>AWAY BATTING</span>
              <h3>{{ detail.away_team }}</h3>
            </div>

            <div class="table-scroll">
              <table class="detail-table batting-table">
                <thead>
                  <tr>
                    <th>球員</th>
                    <th>AB</th>
                    <th>H</th>
                    <th>RBI</th>
                  </tr>
                </thead>

                <tbody>
                  <tr v-if="awayPlayers.length === 0">
                    <td colspan="4" class="no-player-data">
                      暫無打擊數據
                    </td>
                  </tr>

                  <tr
                    v-for="(p, index) in awayPlayers"
                    :key="'away-player-' + index"
                    :class="{ totalRow: isTotalRow(p.name) }"
                  >
                    <td class="player-name">{{ cleanPlayerName(p.name) }}</td>
                    <td>{{ p.ab }}</td>
                    <td>{{ p.h }}</td>
                    <td>{{ p.rbi }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div class="batting-card">
            <div class="batting-card-head home-head">
              <span>HOME BATTING</span>
              <h3>{{ detail.home_team }}</h3>
            </div>

            <div class="table-scroll">
              <table class="detail-table batting-table">
                <thead>
                  <tr>
                    <th>球員</th>
                    <th>AB</th>
                    <th>H</th>
                    <th>RBI</th>
                  </tr>
                </thead>

                <tbody>
                  <tr v-if="homePlayers.length === 0">
                    <td colspan="4" class="no-player-data">
                      暫無打擊數據
                    </td>
                  </tr>

                  <tr
                    v-for="(p, index) in homePlayers"
                    :key="'home-player-' + index"
                    :class="{ totalRow: isTotalRow(p.name) }"
                  >
                    <td class="player-name">{{ cleanPlayerName(p.name) }}</td>
                    <td>{{ p.ab }}</td>
                    <td>{{ p.h }}</td>
                    <td>{{ p.rbi }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { API_BASE } from '../api/cpblApi'
import StateBox from './StateBox.vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  detail: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ''
  }
})

defineEmits(['close'])

const ASSET_BASE = API_BASE.replace(/\/api$/, '')
const TEAM_LOGOS = {
  '中信兄弟': 'brothers.png',
  '味全龍': 'dragons.png',
  '樂天桃猿': 'monkeys.png',
  '統一7-ELEVEn獅': 'lions.png',
  '富邦悍將': 'guardians.png',
  '台鋼雄鷹': 'hawks.png'
}

const totalInnings = computed(() => {
  const awayLength = props.detail?.away_line?.length || 0
  const homeLength = props.detail?.home_line?.length || 0
  return Math.max(awayLength, homeLength, 9)
})

const detailTitle = computed(() => {
  if (!props.detail) return '⚾ 比賽詳情'
  return `${props.detail.away_team} vs ${props.detail.home_team}`
})

const awayPlayers = computed(() => props.detail?.away_players || [])
const homePlayers = computed(() => props.detail?.home_players || [])
const awayRuns = computed(() => props.detail?.away_rhe?.[0] ?? '0')
const homeRuns = computed(() => props.detail?.home_rhe?.[0] ?? '0')
const winnerSide = computed(() => {
  const away = Number(awayRuns.value)
  const home = Number(homeRuns.value)
  if (away > home) return 'away'
  if (home > away) return 'home'
  return ''
})
const winnerText = computed(() => {
  if (winnerSide.value === 'away') return `${props.detail.away_team} 勝`
  if (winnerSide.value === 'home') return `${props.detail.home_team} 勝`
  return '平手'
})
const startersText = computed(() => {
  const away = normalizeText(props.detail?.away_pitcher)
  const home = normalizeText(props.detail?.home_pitcher)
  if (!away && !home) return '尚未公布'
  return `${away || '未公布'} / ${home || '未公布'}`
})
const starterMeta = computed(() => `${props.detail?.away_team || '客隊'} / ${props.detail?.home_team || '主隊'}`)
const mvpText = computed(() => normalizeText(props.detail?.mvp) || '尚未公布')
const mvpMeta = computed(() => {
  if (props.detail?.mvp_note) return props.detail.mvp_note
  if (props.detail?.mvp_team) return `${props.detail.mvp_team} · 官方 MVP`
  return '完賽後同步更新'
})
const decisionText = computed(() => {
  const win = normalizeText(props.detail?.winning_pitcher)
  const lose = normalizeText(props.detail?.losing_pitcher)
  if (!win && !lose) return '尚未公布'
  return `${win || '-'} / ${lose || '-'}`
})
const saveText = computed(() => normalizeText(props.detail?.save_pitcher) ? `救援成功：${props.detail.save_pitcher}` : '無救援成功')

function teamLogo(team) {
  const fileName = TEAM_LOGOS[team] || 'default.png'
  return `${ASSET_BASE}/static/image/teams/${fileName}`
}

function normalizeText(value) {
  return value && value !== '-' && value !== '--' ? value : ''
}

function cleanPlayerName(name = '') {
  if (name === 'Total') return 'Total'

  return name
    .replace(/^\d+/, '')
    .replace(/(LF|RF|CF|SS|2B|3B|1B|DH|C|P)$/g, '')
    .trim()
}

function isTotalRow(name = '') {
  return name === 'Total'
}

watch(
  () => props.show,
  (value) => {
    document.body.style.overflow = value ? 'hidden' : ''
  }
)
</script>
