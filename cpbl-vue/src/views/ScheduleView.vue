<template>
  <div>
    <section class="section-header">
      <div>
        <p class="eyebrow">SCHEDULE</p>
        <h2>{{ SEASON_YEAR }} 一軍賽程</h2>
        <p>依月份與球隊快速查詢賽程，支援月曆與列表兩種檢視模式。</p>
      </div>
      <button class="btn-primary" :disabled="syncing" @click="syncMonth">
        <i
          :class="
            syncing ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-rotate'
          "
        ></i>
        {{ syncing ? "同步中" : `同步 ${currentMonth} 月` }}
      </button>
    </section>

    <section class="filter-bar">
      <div class="filter-group">
        <label>球隊</label>
        <select v-model="selectedTeam" @change="loadSchedule">
          <option value="">所有球隊</option>
          <option v-for="team in teams" :key="team" :value="team">
            {{ team }}
          </option>
        </select>
      </div>

      <div class="month-switcher">
        <button class="btn-soft" @click="changeMonth(-1)">‹</button>
        <strong>{{ currentMonth }} 月</strong>
        <button class="btn-soft" @click="changeMonth(1)">›</button>
      </div>

      <button class="btn-soft today-btn" type="button" @click="goToday">
        <i class="fa-solid fa-location-crosshairs"></i>
        今天
      </button>

      <div class="view-toggle">
        <button
          :class="{ active: viewMode === 'calendar' }"
          @click="viewMode = 'calendar'"
        >
          月曆
        </button>
        <button
          :class="{ active: viewMode === 'list' }"
          @click="viewMode = 'list'"
        >
          列表
        </button>
      </div>
    </section>

    <section class="team-filter-strip schedule-team-strip">
      <button
        type="button"
        :class="{ active: selectedTeam === '' }"
        @click="selectTeam('')"
      >
        <i class="fa-solid fa-border-all"></i>
        全部
      </button>
      <button
        v-for="team in teams"
        :key="team"
        type="button"
        :class="{ active: selectedTeam === team }"
        @click="selectTeam(team)"
      >
        <img :src="teamLogo(team)" :alt="team" />
        {{ shortTeam(team) }}
      </button>
    </section>

    <section v-if="loading" class="game-list">
      <div v-for="i in 4" :key="`schedule-skeleton-${i}`" class="ticket-skeleton">
        <div class="skeleton-line short"></div>
        <div class="skeleton-game-row">
          <div class="skeleton-team"></div>
          <div class="skeleton-score"></div>
          <div class="skeleton-team right"></div>
        </div>
        <div class="skeleton-line"></div>
      </div>
    </section>
    <StateBox
      v-else-if="error"
      type="error"
      title="讀取失敗"
      :message="error"
    />

    <section v-else>
      <div v-if="viewMode === 'calendar'" class="calendar-grid">
        <div v-for="day in weekDays" :key="day" class="calendar-header">
          {{ day }}
        </div>
        <div
          v-for="i in firstDay"
          :key="`empty-${i}`"
          class="calendar-day empty"
        ></div>
        <div
          v-for="day in daysInMonth"
          :key="day"
          :class="[
            'calendar-day',
            {
              'has-game': gamesByDate[dateString(day)]?.length,
              'is-today': dateString(day) === todayDate,
              'is-selected': dateString(day) === selectedDate
            },
          ]"
          @click="showDayDetail(dateString(day))"
        >
          <div class="day-num">{{ day }}</div>
          <span v-if="gamesByDate[dateString(day)]?.length" class="day-game-count">
            {{ gamesByDate[dateString(day)].length }} 場
          </span>
          <div class="game-previews">
            <div
              v-for="game in (gamesByDate[dateString(day)] || []).slice(0, 2)"
              :key="game.id"
              class="mini-game"
            >
              {{ game.away }} vs {{ game.home }}
            </div>
            <div
              v-if="(gamesByDate[dateString(day)] || []).length > 2"
              class="mini-more"
            >
              +{{ gamesByDate[dateString(day)].length - 2 }}
            </div>
          </div>
        </div>
      </div>

      <div v-else>
        <StateBox
          v-if="monthGames.length === 0"
          :title="`${currentMonth} 月查無賽程`"
          message="可以嘗試切換月份、球隊，或先執行同步資料。"
        />
        <div v-for="date in sortedDates" :key="date" class="schedule-group">
          <div class="schedule-date-title">
            <span>{{ date }}</span>
            <small>{{ getWeekdayStr(date) }}</small>
          </div>
          <div class="game-list">
            <GameCard
              v-for="game in groupedMonthGames[date]"
              :key="game.id"
              :game="game"
              :show-actions="false"
              @open-detail="$emit('open-game', $event)"
            />
          </div>
        </div>
      </div>

      <section v-if="selectedDate" class="day-detail">
        <div class="schedule-date-title">
          <span>{{ selectedDate }}</span>
          <small>賽事詳情</small>
        </div>
        <div class="game-list">
          <GameCard
            v-for="game in dayGames"
            :key="game.id"
            :game="game"
            :show-actions="false"
            @open-detail="$emit('open-game', $event)"
          />
        </div>
      </section>
    </section>
  </div>
</template>

<script setup>
import { computed, inject, onMounted, onUnmounted, ref } from "vue";
import { API_BASE, cpblApi } from "../api/cpblApi";
import { SEASON_YEAR, getTodayMMDD, getWeekdayStr, groupBy } from "../utils";
import StateBox from "../components/StateBox.vue";
import GameCard from "../components/GameCard.vue";
import { applyGameDetailUpdate, hydrateMissingGameDetails } from "../composables/useGameDetailUpdate";

defineEmits(["open-game"]);

const notify = inject('notify', () => {})
const ASSET_BASE = API_BASE.replace(/\/api$/, '')
const teams = [
  "中信兄弟",
  "味全龍",
  "樂天桃猿",
  "統一7-ELEVEn獅",
  "富邦悍將",
  "台鋼雄鷹",
];
const teamLogoFiles = {
  中信兄弟: 'brothers.png',
  味全龍: 'dragons.png',
  樂天桃猿: 'monkeys.png',
  '統一7-ELEVEn獅': 'lions.png',
  富邦悍將: 'guardians.png',
  台鋼雄鷹: 'hawks.png'
}
const weekDays = ["日", "一", "二", "三", "四", "五", "六"];

const selectedTeam = ref("");
const currentMonth = ref(new Date().getMonth() + 1);
const viewMode = ref("calendar");
const games = ref([]);
const selectedDate = ref("");
const todayDate = getTodayMMDD()
const loading = ref(false);
const syncing = ref(false);
const error = ref("");

const firstDay = computed(() =>
  new Date(SEASON_YEAR, currentMonth.value - 1, 1).getDay(),
);
const daysInMonth = computed(() =>
  new Date(SEASON_YEAR, currentMonth.value, 0).getDate(),
);
const monthGames = computed(() =>
  games.value.filter(
    (g) => Number((g.date || "").split("/")[0]) === currentMonth.value,
  ),
);
const gamesByDate = computed(() =>
  groupBy(games.value, (g) => g.date || "未定"),
);
const groupedMonthGames = computed(() =>
  groupBy(monthGames.value, (g) => g.date || "未定"),
);
const sortedDates = computed(() => Object.keys(groupedMonthGames.value).sort());
const dayGames = computed(() =>
  games.value.filter((g) => g.date === selectedDate.value),
);

function dateString(day) {
  return `${String(currentMonth.value).padStart(2, "0")}/${String(day).padStart(2, "0")}`;
}

function teamLogo(team) {
  return `${ASSET_BASE}/static/image/teams/${teamLogoFiles[team] || 'default.png'}`
}

function shortTeam(team) {
  return team.replace('7-ELEVEn', '7-11')
}

function selectTeam(team) {
  selectedTeam.value = team
  loadSchedule()
}

async function loadSchedule() {
  loading.value = true;
  error.value = "";
  selectedDate.value = "";
  try {
    games.value = await cpblApi.getGames({ team: selectedTeam.value });
  } catch {
    error.value = "賽程資料讀取失敗，請確認 Flask 是否啟動。";
  } finally {
    loading.value = false;
  }
}

function changeMonth(delta) {
  currentMonth.value += delta;
  if (currentMonth.value > 12) currentMonth.value = 1;
  if (currentMonth.value < 1) currentMonth.value = 12;
  selectedDate.value = "";
}

function goToday() {
  const today = getTodayMMDD()
  currentMonth.value = Number(today.split('/')[0])
  selectedDate.value = today
  viewMode.value = 'calendar'
}

async function showDayDetail(date) {
  selectedDate.value = date;
  await hydrateMissingGameDetails(games, cpblApi, { date, limit: 4 })
}

async function syncMonth() {
  syncing.value = true;
  try {
    await cpblApi.updateMonth(currentMonth.value, SEASON_YEAR);
    await loadSchedule();
    notify({ type: 'success', title: '同步完成', message: `${currentMonth.value} 月賽程已更新。` });
  } catch {
    notify({ type: 'error', title: '同步失敗', message: '請確認後端或爬蟲是否正常。' });
  } finally {
    syncing.value = false;
  }
}

function handleGameDetailUpdated(event) {
  applyGameDetailUpdate(games, event)
}

onMounted(() => {
  window.addEventListener('cpbl-game-detail-updated', handleGameDetailUpdated)
  loadSchedule()
});

onUnmounted(() => {
  window.removeEventListener('cpbl-game-detail-updated', handleGameDetailUpdated)
});
</script>
