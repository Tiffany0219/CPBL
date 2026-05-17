<template>
  <div>
    <section class="section-header">
      <div>
        <p class="eyebrow">FAN TIMELINE</p>
        <h2>我的看球足跡</h2>
        <p>把票夾裡的觀賽照片與心得整理成時間線，留下每一場比賽的記憶。</p>
      </div>

      <button class="btn-soft" type="button" @click="loadTimeline">
        <i class="fa-solid fa-rotate"></i>
        重新整理
      </button>
    </section>

    <section class="timeline-stats">
      <article class="lineup-summary-card">
        <span>觀賽紀錄</span>
        <strong>{{ timeline.length }}</strong>
      </article>
      <article class="lineup-summary-card">
        <span>造訪球場</span>
        <strong>{{ visitedLocations }}</strong>
      </article>
      <article class="lineup-summary-card">
        <span>最近一場</span>
        <strong>{{ latestDate }}</strong>
      </article>
    </section>

    <StateBox
      v-if="timeline.length === 0"
      title="還沒有看球足跡"
      message="到首頁賽事卡片新增觀賽票夾，這裡就會自動長出你的球迷時間線。"
    />

    <section v-else class="fan-timeline">
      <article v-for="ticket in timeline" :key="ticket.id" class="timeline-item">
        <div class="timeline-dot"></div>
        <div class="timeline-card">
          <div class="timeline-image">
            <img v-if="ticket.image" :src="ticket.image" alt="觀賽照片" />
            <div v-else>
              <i class="fa-regular fa-image"></i>
              <span>沒有照片</span>
            </div>
          </div>

          <div class="timeline-body">
            <span>{{ ticket.date || '未記錄日期' }} · {{ ticket.location || '未知球場' }}</span>
            <h3>{{ ticket.away }} vs {{ ticket.home }}</h3>
            <p>{{ ticket.note || '這場比賽還沒有心得。' }}</p>
            <small>{{ formatDate(ticket.createdAt) }}</small>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, inject, onMounted, ref } from 'vue'
import { cpblApi } from '../api/cpblApi'
import StateBox from '../components/StateBox.vue'
import { useGameMemory } from '../composables/useGameMemory'

const { getAllTickets } = useGameMemory()
const auth = inject('auth', null)
const timeline = ref([])

const visitedLocations = computed(() => new Set(timeline.value.map(ticket => ticket.location).filter(Boolean)).size)
const latestDate = computed(() => timeline.value[0]?.date || '-')

async function loadTimeline() {
  try {
    if (auth?.token?.value) {
      timeline.value = await cpblApi.getUserTickets(auth.token.value)
      return
    }
  } catch {
    timeline.value = []
  }
  timeline.value = getAllTickets()
}

function formatDate(value) {
  if (!value) return '未記錄建立時間'
  return new Date(value).toLocaleString('zh-TW', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(loadTimeline)
</script>
