<template>
  <div v-if="show" class="modal" style="display:block;">
    <div class="modal-content game-detail-modal">
      <button class="modal-close" @click="$emit('close')">
        &times;
      </button>

      <div class="detail-hero">
        <p class="eyebrow">GAME DETAIL</p>
        <h2>{{ detailTitle }}</h2>
        <p v-if="detail">
          逐局比分、R-H-E 統計與兩隊打擊數據
        </p>
      </div>

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
        <!-- 比賽摘要 -->
        <section class="detail-score-ticket">
          <div class="detail-team">
            <span>AWAY</span>
            <strong>{{ detail.away_team }}</strong>
            <b>{{ detail.away_rhe?.[0] ?? '0' }}</b>
          </div>

          <div class="detail-vs">
            <span>FINAL SCORE</span>
            <em>VS</em>
          </div>

          <div class="detail-team right">
            <span>HOME</span>
            <strong>{{ detail.home_team }}</strong>
            <b>{{ detail.home_rhe?.[0] ?? '0' }}</b>
          </div>
        </section>

        <!-- 逐局比分 -->
        <section class="detail-section">
          <div class="detail-section-title">
            <div>
              <p class="eyebrow">LINE SCORE</p>
              <h3>逐局比分</h3>
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