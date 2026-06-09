<template>
  <div>
    <section class="section-header">
      <div>
        <p class="eyebrow">LATEST NEWS</p>
        <h2>最新消息</h2>
        <p>即時整理 CPBL 官方賽事新聞，掌握球隊近況與比賽焦點。</p>
      </div>

      <button class="btn-primary" type="button" :disabled="loading" @click="loadNews">
        <i :class="loading ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-rotate'"></i>
        {{ loading ? '更新中' : '重新整理' }}
      </button>
    </section>

    <section class="news-search-panel">
      <div class="news-search-box">
        <i class="fa-solid fa-magnifying-glass"></i>
        <input
          v-model="keyword"
          type="search"
          placeholder="搜尋球隊、球員、賽事或關鍵字..."
        />
        <button v-if="keyword" type="button" @click="keyword = ''">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <div class="news-search-meta">
        <span>{{ searchSummary }}</span>
        <button
          v-for="tag in quickKeywords"
          :key="tag"
          type="button"
          :class="{ active: keyword === tag }"
          @click="keyword = tag"
        >
          {{ tag }}
        </button>
      </div>
    </section>

    <section class="news-list">
      <StateBox v-if="loading" type="loading" message="正在讀取 CPBL 最新消息..." />

      <StateBox
        v-else-if="error"
        type="error"
        title="新聞讀取異常"
        :message="error"
      />

      <StateBox
        v-else-if="filteredNews.length === 0"
        title="查無相關新聞"
        message="換個球隊、球員或關鍵字再搜尋看看。"
      />

      <template v-else>
        <article
          v-for="item in filteredNews"
          :key="`${item.date}-${item.title}`"
          class="news-card"
        >
          <a
            v-if="item.image"
            class="news-image"
            :href="item.url || cpblNewsUrl"
            target="_blank"
            rel="noreferrer"
            :style="{ backgroundImage: `url(${item.image})` }"
            :title="item.title"
          ></a>

          <div v-else class="news-image fallback">
            <i class="fa-solid fa-baseball"></i>
          </div>

          <div class="news-date">
            <strong>{{ item.date || item.time || '-' }}</strong>
            <span>{{ item.category || item.tag || '消息' }}</span>
          </div>

          <div class="news-body">
            <a
              class="news-title-link"
              :href="item.url || cpblNewsUrl"
              target="_blank"
              rel="noreferrer"
            >
              {{ item.title || '未命名消息' }}
            </a>
            <p>{{ item.summary || item.content || item.description || '點擊標題前往 CPBL 官網閱讀完整內容。' }}</p>
            <div class="news-tags">
              <span>{{ item.tag || item.type || 'CPBL' }}</span>
              <span v-if="item.source">{{ item.source }}</span>
            </div>
          </div>
        </article>
      </template>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { cpblApi } from '../api/cpblApi'
import { SEASON_YEAR } from '../utils'
import StateBox from '../components/StateBox.vue'

const cpblNewsUrl = 'https://www.cpbl.com.tw/xmdoc'
const loading = ref(false)
const error = ref('')
const news = ref([])
const keyword = ref('')
const quickKeywords = ['中信兄弟', '味全龍', '樂天桃猿', '統一獅', '富邦悍將', '台鋼雄鷹']

const fallbackNews = [
  { title: '歡迎使用 GoBase 中職數據平台', date: String(SEASON_YEAR), category: '系統公告', summary: '本平台提供賽程查詢、球隊戰績、數據統計、球員抽卡與打線收藏功能。', tag: '系統', source: 'GoBase', url: cpblNewsUrl },
  { title: '賽程資料支援手動同步', date: String(SEASON_YEAR), category: '資料更新', summary: '使用者可於首頁或賽程頁面觸發同步，系統將自動抓取 CPBL 官網資料。', tag: '資料同步', source: 'GoBase', url: cpblNewsUrl },
  { title: '球員抽卡與收藏冊已開放', date: String(SEASON_YEAR), category: '互動功能', summary: '可透過球員池隨機抽取球員卡牌，並在收藏冊與我的打線中使用。', tag: '收藏冊', source: 'GoBase', url: cpblNewsUrl }
]

const filteredNews = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  if (!query) return news.value

  return news.value.filter(item => {
    const text = [
      item.title,
      item.summary,
      item.content,
      item.description,
      item.category,
      item.tag,
      item.type,
      item.source,
      item.date,
      item.time
    ].filter(Boolean).join(' ').toLowerCase()

    return text.includes(query)
  })
})

const searchSummary = computed(() => {
  if (!keyword.value.trim()) return `目前顯示 ${news.value.length} 則消息`
  return `找到 ${filteredNews.value.length} / ${news.value.length} 則相關消息`
})

async function loadNews() {
  loading.value = true
  error.value = ''

  try {
    const data = await cpblApi.getNews({ limit: 30 })
    news.value = Array.isArray(data) && data.length ? data : fallbackNews
  } catch (err) {
    console.error(err)
    news.value = fallbackNews
    error.value = '暫時無法連線到新聞 API，已顯示系統備援消息。'
  } finally {
    loading.value = false
  }
}

onMounted(loadNews)
</script>
