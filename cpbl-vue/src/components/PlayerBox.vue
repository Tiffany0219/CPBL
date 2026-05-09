<template>
  <section>
    <h3 :style="{ borderLeftColor: color }">{{ title }}</h3>
    <table class="detail-table">
      <thead>
        <tr><th>球員</th><th>打數</th><th>安打</th><th>打點</th></tr>
      </thead>
      <tbody>
        <tr v-if="!players || players.length === 0">
          <td colspan="4" class="muted-cell">比賽尚未開始或暫無球員數據</td>
        </tr>
        <tr v-for="player in players" :key="player.name">
          <td>{{ player.name }}</td>
          <td>{{ player.ab }}</td>
          <td>{{ player.h }}</td>
          <td>{{ player.rbi }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup>
defineProps({
  title: String,
  color: String,
  players: Array
})
</script>
