<template>
  <button
    :class="['ai-assistant-trigger', { open }]"
    type="button"
    :aria-expanded="open"
    aria-label="開啟 GoBase AI"
    title="GoBase AI"
    @click="open = !open"
  >
    <img
      v-if="!open"
      class="ai-assistant-trigger-image"
      :src="aiBallImage"
      alt=""
      aria-hidden="true"
    >
    <i v-else class="fa-solid fa-xmark"></i>
  </button>

  <aside v-if="open" class="ai-assistant-panel" aria-label="GoBase AI 球迷助理">
    <header class="ai-assistant-head">
      <div class="ai-assistant-avatar">
        <img :src="aiBallImage" alt="" aria-hidden="true">
      </div>
      <div>
        <span>GOBASE AI</span>
        <strong>球迷助理</strong>
      </div>
      <button type="button" title="清除對話" aria-label="清除對話" @click="clearMessages">
        <i class="fa-solid fa-trash-can"></i>
      </button>
    </header>

    <div ref="messageList" class="ai-assistant-messages">
      <article
        v-for="message in messages"
        :key="message.id"
        :class="['ai-message', message.role]"
      >
        <span>{{ message.role === 'assistant' ? 'GoBase AI' : '你' }}</span>
        <p>{{ message.content }}</p>
      </article>

      <article v-if="loading" class="ai-message assistant loading">
        <span>GoBase AI</span>
        <div class="ai-typing" aria-label="AI 正在回答">
          <i></i><i></i><i></i>
        </div>
      </article>
    </div>

    <div v-if="messages.length <= 1" class="ai-quick-prompts">
      <button v-for="prompt in quickPrompts" :key="prompt" type="button" @click="sendPrompt(prompt)">
        {{ prompt }}
      </button>
    </div>

    <form class="ai-assistant-compose" @submit.prevent="sendMessage">
      <textarea
        v-model="draft"
        rows="2"
        maxlength="1000"
        placeholder="問賽程、戰績、規則或卡牌打線..."
        @keydown.enter.exact.prevent="sendMessage"
      ></textarea>
      <button type="submit" :disabled="loading || !draft.trim()" title="送出" aria-label="送出問題">
        <i class="fa-solid fa-paper-plane"></i>
      </button>
    </form>

    <small class="ai-assistant-note">
      AI 依 GoBase 現有資料回答，重要資訊請以官方公告為準。
    </small>
  </aside>
</template>

<script setup>
import { inject, nextTick, ref } from 'vue'
import { cpblApi } from '../api/cpblApi'
import aiBallImage from '../assets/ai-assistant-ball.jpeg'

const props = defineProps({
  activePage: {
    type: String,
    default: 'home'
  }
})

const auth = inject('auth', null)
const open = ref(false)
const loading = ref(false)
const draft = ref('')
const messageList = ref(null)
const messages = ref([welcomeMessage()])
const quickPrompts = [
  '今天有什麼比賽？',
  '今天去洲際要帶雨衣嗎？',
  '幫我看目前球隊戰績',
  '解釋棒球的救援成功',
  '推薦我的卡牌打線'
]

function welcomeMessage() {
  return {
    id: `welcome-${Date.now()}`,
    role: 'assistant',
    content: '嗨，我是 GoBase AI。可以問我今日賽程、比賽數據、棒球規則，登入後也能聊你的卡牌與打線。'
  }
}

function clearMessages() {
  messages.value = [welcomeMessage()]
  draft.value = ''
}

function sendPrompt(prompt) {
  draft.value = prompt
  sendMessage()
}

async function sendMessage() {
  const content = draft.value.trim()
  if (!content || loading.value) return

  messages.value.push({
    id: `user-${Date.now()}`,
    role: 'user',
    content
  })
  draft.value = ''
  loading.value = true
  await scrollToBottom()

  try {
    const conversation = messages.value
      .filter(message => ['user', 'assistant'].includes(message.role))
      .slice(-10)
      .map(({ role, content: text }) => ({ role, content: text }))
    const result = await cpblApi.askAi(conversation, props.activePage, auth?.token?.value)
    messages.value.push({
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: result.answer
    })
  } catch (error) {
    messages.value.push({
      id: `error-${Date.now()}`,
      role: 'assistant',
      content: normalizeError(error)
    })
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

function normalizeError(error) {
  try {
    const parsed = JSON.parse(error?.message || '')
    return parsed.error || 'AI 暫時無法回應，請稍後再試。'
  } catch {
    return error?.message || 'AI 暫時無法回應，請稍後再試。'
  }
}

async function scrollToBottom() {
  await nextTick()
  if (messageList.value) {
    messageList.value.scrollTop = messageList.value.scrollHeight
  }
}
</script>
