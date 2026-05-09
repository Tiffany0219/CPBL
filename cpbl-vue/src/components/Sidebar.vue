<template>
  <nav class="sidebar">
    <h1 class="brand-logo">⚾GOBASE<span>!</span></h1>

    <ul class="nav-menu">
      <li v-for="item in menuItems" :key="item.key" :class="{ active: activePage === item.key }">
        <button type="button" @click="$emit('change-page', item.key)">
          <i :class="item.icon"></i>
          <span>{{ item.label }}</span>
        </button>
      </li>
    </ul>
  </nav>
</template>

<script setup>
defineProps({
  activePage: {
    type: String,
    required: true
  }
})

defineEmits(['change-page'])

const menuItems = [
  { key: 'home', label: '首頁看板', icon: 'fa-solid fa-house' },
  { key: 'news', label: '最新消息', icon: 'fa-solid fa-newspaper' },
  { key: 'schedule', label: '賽程查詢', icon: 'fa-solid fa-calendar' },
  { key: 'standings', label: '球隊戰績', icon: 'fa-solid fa-ranking-star' },
  { key: 'stats', label: '數據統計', icon: 'fa-solid fa-chart-line' },
  { key: 'gacha', label: '球員抽卡', icon: 'fa-solid fa-box-open' },
  { key: 'collection', label: '球員收藏', icon: 'fa-solid fa-layer-group' },
  { key: 'lineup', label: '我的打線', icon: 'fa-solid fa-users-rectangle' },
  { key: 'sync', label: '同步中心', icon: 'fa-solid fa-arrows-rotate' }
]
</script>
