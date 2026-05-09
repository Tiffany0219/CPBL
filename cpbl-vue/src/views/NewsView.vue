<template>
  <div>
    <section class="section-header">
      <div>
        <p class="eyebrow">LATEST NEWS</p>
        <h2>最新消息</h2>
        <p>整理中華職棒近期賽事、球員動態與活動公告。</p>
      </div>
    </section>

    <section class="news-list">
      <StateBox v-if="loading" type="loading" message="正在讀取最新消息..." />
      <article v-for="item in news" v-else :key="item.title" class="news-card">
        <div class="news-date">
          <strong>{{ item.date || item.time || '2026' }}</strong>
          <span>{{ item.category || item.tag || '消息' }}</span>
        </div>
        <div class="news-body">
          <h3>{{ item.title || '未命名消息' }}</h3>
          <p>{{ item.summary || item.content || item.description || '尚無詳細內容。' }}</p>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { cpblApi } from '../api/cpblApi'
import StateBox from '../components/StateBox.vue'

const loading = ref(false)
const news = ref([])

const fallbackNews = [
  { title: '歡迎使用 GoBase 中職數據平台', date: '2026', category: '系統公告', summary: '本平台提供賽程查詢、球隊戰績、數據統計與球員抽卡功能。' },
  { title: '賽程資料支援手動同步', date: '2026', category: '資料更新', summary: '使用者可於首頁或賽程頁面觸發同步，系統將自動抓取 CPBL 官網資料。' },
  { title: '球員抽卡功能已開放', date: '2026', category: '互動功能', summary: '可透過球員池隨機抽取球員卡牌，增加資料查詢的趣味性。' }
]

onMounted(async () => {
  loading.value = true
  try {
    const data = await cpblApi.getNews()
    news.value = Array.isArray(data) && data.length ? data : fallbackNews
  } catch {
    news.value = fallbackNews
  } finally {
    loading.value = false
  }
})
</script>
