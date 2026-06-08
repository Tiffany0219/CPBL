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

        <!-- 歷史對戰與勝率預測 -->
        <section v-if="predictionData.hasData" class="detail-section detail-prediction-section">
          <div class="detail-section-title">
            <div>
              <p class="eyebrow">PREDICTION & H2H</p>
              <h3>對戰數據與勝率預估</h3>
            </div>
            <div class="rhe-pills">
              <span>數據指標預估</span>
            </div>
          </div>

          <div class="prediction-bar-wrapper">
            <div class="prediction-bar-header">
              <span class="team-label away" :style="{ color: awayTeamColor }">
                {{ detail.away_team }} {{ predictionData.awayWinRate }}%
              </span>
              <span class="prediction-vs">VS</span>
              <span class="team-label home" :style="{ color: homeTeamColor }">
                {{ predictionData.homeWinRate }}% {{ detail.home_team }}
              </span>
            </div>

            <div class="prediction-meter-bg" :style="{ backgroundColor: homeTeamColor }">
              <div
                class="prediction-meter-fill"
                :style="{
                  width: `${predictionData.awayWinRate}%`,
                  backgroundColor: awayTeamColor,
                  boxShadow: `0 0 12px ${awayTeamColor}80`
                }"
              ></div>
            </div>
            <p class="prediction-hint">
              *勝率根據雙方本季整體勝率 (40%)、歷史對戰 (40%) 及近期十場與連勝敗近況 (20%) 計算而得。
            </p>
          </div>

          <div class="matchup-table-wrapper">
            <div class="matchup-table-header">
              <span>{{ detail.away_team }}</span>
              <span>比較項目</span>
              <span>{{ detail.home_team }}</span>
            </div>
            <div class="matchup-table-body">
              <div
                v-for="(stat, idx) in predictionData.compareStats"
                :key="'stat-' + idx"
                class="matchup-row"
              >
                <span class="matchup-val away">{{ stat.away }}</span>
                <span class="matchup-label">{{ stat.label }}</span>
                <span class="matchup-val home">{{ stat.home }}</span>
              </div>
            </div>
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

        <section class="detail-section play-by-play-section">
          <div class="detail-section-title">
            <div>
              <p class="eyebrow">LIVE LOG</p>
              <h3>文字轉播</h3>
            </div>
            <div class="rhe-pills">
              <span>{{ playByPlay.length }} 則事件</span>
            </div>
          </div>

          <div v-if="playByPlay.length === 0" class="no-play-data">
            <i class="fa-solid fa-radio"></i>
            <strong>尚無文字轉播資料</strong>
            <span>比賽開始後會顯示打席、跑壘與壘包狀態。</span>
          </div>

          <div v-else class="play-log-list">
            <article
              v-for="event in playByPlay"
              :key="event.id"
              :class="['play-log-item', { scoring: event.is_scoring }]"
            >
              <div class="play-log-time">
                <strong>{{ event.inning }}</strong>
                <span>{{ event.team }}</span>
              </div>

              <div class="play-log-body">
                <div class="play-log-head">
                  <strong>{{ event.hitter || '打者' }}</strong>
                  <span>{{ event.result || 'PLAY' }}</span>
                  <em>{{ event.score_text }}</em>
                </div>

                <p>{{ event.content }}</p>

                <div class="play-log-meta">
                  <span>投手 {{ event.pitcher || '-' }}</span>
                  <span>{{ event.outs }} out</span>
                  <span>B-S {{ event.count }}</span>
                  <span>P {{ event.pitch_count }}</span>
                </div>

                <div class="base-state-row">
                  <BaseDiamond label="PLAY 前" :bases="event.bases_before" />
                  <i class="fa-solid fa-arrow-right"></i>
                  <BaseDiamond label="PLAY 後" :bases="event.bases_after" />
                </div>
              </div>
            </article>
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
import { computed, ref, watch } from 'vue'
import { API_BASE, cpblApi } from '../api/cpblApi'
import { TEAM_COLORS } from '../composables/usePlayerCollection'
import StateBox from './StateBox.vue'
import BaseDiamond from './BaseDiamond.vue'

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
const playByPlay = computed(() => props.detail?.play_by_play || [])
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

const standings = ref(null)
const loadingStandings = ref(false)

async function loadStandings() {
  if (standings.value) return
  loadingStandings.value = true
  try {
    standings.value = await cpblApi.getStandings()
  } catch (err) {
    console.error('載入戰績失敗', err)
  } finally {
    loadingStandings.value = false
  }
}

function normalizeTeamName(name) {
  if (!name) return ''
  const n = name.trim()
  if (n.includes('統一') || n.includes('獅')) return '統一7-ELEVEn獅'
  if (n.includes('兄弟')) return '中信兄弟'
  if (n.includes('桃猿') || n.includes('樂天')) return '樂天桃猿'
  if (n.includes('龍') || n.includes('味全')) return '味全龍'
  if (n.includes('悍將') || n.includes('富邦')) return '富邦悍將'
  if (n.includes('雄鷹') || n.includes('台鋼')) return '台鋼雄鷹'
  return n
}

const findTeamRow = (teamName) => {
  if (!standings.value?.h2h) return null
  const target = normalizeTeamName(teamName)
  return standings.value.h2h.find(row => {
    const rowTeam = row["排名球隊"] ? row["排名球隊"].replace(/^\d+/, '').trim() : ''
    return normalizeTeamName(rowTeam) === target
  })
}

const awayTeamColor = computed(() => TEAM_COLORS[props.detail?.away_team] || '#1f5f99')
const homeTeamColor = computed(() => TEAM_COLORS[props.detail?.home_team] || '#0f766e')

const predictionData = computed(() => {
  if (!props.detail || !standings.value?.h2h) {
    return { awayWinRate: 50, homeWinRate: 50, hasData: false }
  }

  const awayTeam = props.detail.away_team
  const homeTeam = props.detail.home_team

  const awayRow = findTeamRow(awayTeam)
  const homeRow = findTeamRow(homeTeam)

  if (!awayRow || !homeRow) {
    return { awayWinRate: 50, homeWinRate: 50, hasData: false }
  }

  // 1. Overall win rate
  const awayOverall = parseFloat(awayRow["勝率"]) || 0.5
  const homeOverall = parseFloat(homeRow["勝率"]) || 0.5

  // 2. Head-to-Head win rate
  const normalizedHome = normalizeTeamName(homeTeam)
  let h2hRecord = ''
  for (const key of Object.keys(awayRow)) {
    if (normalizeTeamName(key) === normalizedHome) {
      h2hRecord = awayRow[key]
      break
    }
  }

  let awayH2HWinRate = 0.5
  if (h2hRecord && h2hRecord.includes('-')) {
    const parts = h2hRecord.split('-').map(Number)
    if (parts.length >= 3) {
      const w = parts[0]
      const l = parts[2]
      if (w + l > 0) {
        awayH2HWinRate = w / (w + l)
      }
    }
  }

  const homeH2HWinRate = 1 - awayH2HWinRate

  // 3. Streak modifier
  const parseStreak = (streakStr) => {
    if (!streakStr) return 0
    const match = streakStr.match(/(勝|敗)(\d+)/)
    if (match) {
      const type = match[1]
      const val = parseInt(match[2], 10)
      return type === '勝' ? val * 0.02 : -val * 0.02
    }
    return 0
  }
  const awayStreakMod = Math.max(-0.06, Math.min(0.06, parseStreak(awayRow["連勝/連敗"])))
  const homeStreakMod = Math.max(-0.06, Math.min(0.06, parseStreak(homeRow["連勝/連敗"])))

  // 4. Calculate weighted score
  const awayScore = (awayOverall * 0.4) + (awayH2HWinRate * 0.4) + (0.5 + awayStreakMod) * 0.2
  const homeScore = (homeOverall * 0.4) + (homeH2HWinRate * 0.4) + (0.5 + homeStreakMod) * 0.2

  // Normalize
  let awayWinPercent = Math.round((awayScore / (awayScore + homeScore)) * 100)
  awayWinPercent = Math.max(15, Math.min(85, awayWinPercent))
  const homeWinPercent = 100 - awayWinPercent

  // Gather compare stats
  const compareStats = [
    {
      label: '聯盟排名',
      away: awayRow["排名球隊"] ? '第 ' + (awayRow["排名球隊"].match(/^\d+/)?.[0] || '-') : '-',
      home: homeRow["排名球隊"] ? '第 ' + (homeRow["排名球隊"].match(/^\d+/)?.[0] || '-') : '-'
    },
    {
      label: '整體勝率',
      away: `${(awayOverall * 100).toFixed(1)}%`,
      home: `${(homeOverall * 100).toFixed(1)}%`
    },
    {
      label: '近十場戰績',
      away: awayRow["近十場戰績"] || '-',
      home: homeRow["近十場戰績"] || '-'
    },
    {
      label: '目前近況',
      away: awayRow["連勝/連敗"] || '-',
      home: homeRow["連勝/連敗"] || '-'
    },
    {
      label: '主/客場戰績',
      away: `客場 ${awayRow["客場戰績"] || '-'}`,
      home: `主場 ${homeRow["主場戰績"] || '-'}`
    },
    {
      label: '本季對戰紀錄',
      away: h2hRecord ? `${h2hRecord.split('-')[0]} 勝 ${h2hRecord.split('-')[2]} 敗` : '無交手紀錄',
      home: h2hRecord ? `${h2hRecord.split('-')[2]} 勝 ${h2hRecord.split('-')[0]} 敗` : '無交手紀錄'
    }
  ]

  return {
    awayWinRate: awayWinPercent,
    homeWinRate: homeWinPercent,
    compareStats,
    hasData: true
  }
})

watch(
  () => props.show,
  (value) => {
    document.body.style.overflow = value ? 'hidden' : ''
    if (value) {
      loadStandings()
    }
  }
)
</script>
