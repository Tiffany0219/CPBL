<template>
  <div v-if="show" class="modal" style="display:block;">
    <div class="modal-content ticket-modal">
      <button class="modal-close" @click="$emit('close')">
        &times;
      </button>

      <div class="ticket-modal-header">
        <p class="eyebrow">MY GAME TICKET</p>
        <h2>觀賽票夾</h2>
        <p v-if="game">
          {{ game.date }} · {{ game.location || '未知球場' }} ·
          {{ game.away }} vs {{ game.home }}
          <span v-if="inningLabel" class="ticket-modal-inning">{{ inningLabel }}</span>
        </p>
      </div>

      <div v-if="game" class="ticket-preview-card">
        <div class="ticket-preview-score">
          <strong>{{ game.away }}</strong>
          <span>{{ game.away_score ?? '-' }} : {{ game.home_score ?? '-' }}</span>
          <strong>{{ game.home }}</strong>
        </div>
        <div v-if="inningLabel" class="ticket-preview-inning">
          <i class="fa-solid fa-baseball"></i>
          {{ inningLabel }}
        </div>
      </div>

      <div class="ticket-count-banner">
        <i class="fa-solid fa-ticket"></i>
        這場比賽目前收藏了
        <strong>{{ tickets.length }}</strong>
        筆觀賽紀錄
      </div>

      <!-- 新增票夾表單 -->
      <section class="ticket-add-section">
        <div class="ticket-form">
          <label class="upload-box">
            <input type="file" accept="image/*" @change="handleImageUpload" />

            <template v-if="previewImage">
              <img :src="previewImage" alt="票券或現場照片" />
            </template>

            <template v-else>
              <div>
                <i class="fa-solid fa-camera"></i>
                <span>新增紙本票券 / 現場照片</span>
              </div>
            </template>
          </label>

          <div>
            <label class="form-label">觀賽心得</label>
            <textarea
              v-model="note"
              class="ticket-note"
              placeholder="例如：第一次去新莊看球、今天氣氛超好、最喜歡第七局那支安打..."
            ></textarea>
          </div>
        </div>

        <div class="ticket-modal-actions">
          <button class="btn-soft" @click="resetForm">
            <i class="fa-solid fa-eraser"></i>
            清空表單
          </button>

          <button class="btn-primary" @click="save">
            <i class="fa-solid fa-plus"></i>
            新增到票夾
          </button>
        </div>
      </section>

      <!-- 已收藏票夾內容 -->
      <section class="ticket-gallery" v-if="tickets.length > 0">
        <div class="ticket-gallery-title">
          <h3>已收藏的觀賽紀錄</h3>
          <span>{{ tickets.length }} 筆</span>
        </div>

        <div class="ticket-gallery-grid">
          <article
            v-for="ticket in tickets"
            :key="ticket.id"
            class="ticket-memory-card"
          >
            <button
              class="ticket-delete-btn"
              title="刪除這筆紀錄"
              @click="$emit('remove', ticket.id)"
            >
              <i class="fa-solid fa-trash"></i>
            </button>

            <button
              v-if="ticket.image"
              class="ticket-view-btn"
              title="查看大圖"
              @click="openPreview(ticket)"
            >
              <i class="fa-solid fa-up-right-and-down-left-from-center"></i>
            </button>

            <div class="ticket-memory-image">
              <img
                v-if="ticket.image"
                :src="ticket.image"
                alt="觀賽照片"
              />

              <div v-else class="ticket-memory-empty">
                <i class="fa-regular fa-image"></i>
                <span>沒有照片</span>
              </div>
            </div>

            <div class="ticket-memory-body">
              <p>{{ ticket.note || '尚未填寫心得' }}</p>
              <small>{{ formatDate(ticket.createdAt) }}</small>
            </div>
          </article>
        </div>
      </section>

      <section v-else class="ticket-empty-note">
        <i class="fa-regular fa-folder-open"></i>
        <p>這場比賽還沒有票夾紀錄，先新增一張票券或現場照片吧！</p>
      </section>

      <!-- 查看大圖 -->
      <div
        v-if="previewTicket"
        class="ticket-image-viewer"
        @click="closePreview"
      >
        <div class="ticket-image-viewer-card" @click.stop>
          <button class="ticket-image-close" @click="closePreview">
            &times;
          </button>

          <img
            v-if="previewTicket.image"
            :src="previewTicket.image"
            alt="觀賽照片大圖"
          />

          <div class="ticket-image-caption">
            <p>{{ previewTicket.note || '尚未填寫心得' }}</p>
            <small>{{ formatDate(previewTicket.createdAt) }}</small>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, inject, ref, watch } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  game: {
    type: Object,
    default: null
  },
  tickets: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close', 'save', 'remove'])
const notify = inject('notify', () => {})

const note = ref('')
const previewImage = ref('')
const previewTicket = ref(null)

const inningLabel = computed(() => {
  const value = cleanValue(props.game?.current_inning || props.game?.game_time)
  if (!value || value === 'LIVE' || value === 'Final') return ''
  if (props.game?.status !== 'LIVE' && !value.includes('局')) return ''
  return value.includes('目前') ? value : `目前 ${value}`
})

watch(
  () => props.show,
  (value) => {
    if (value) {
      resetForm()
      previewTicket.value = null
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
  }
)

function handleImageUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return

  const reader = new FileReader()

  reader.onload = () => {
    previewImage.value = reader.result
  }

  reader.readAsDataURL(file)
}

function save() {
  if (!previewImage.value && !note.value.trim()) {
    notify({ type: 'warning', title: '還不能新增', message: '請至少上傳一張照片或填寫心得。' })
    return
  }

  emit('save', {
    note: note.value.trim(),
    image: previewImage.value
  })

  resetForm()
}

function resetForm() {
  note.value = ''
  previewImage.value = ''
}

function openPreview(ticket) {
  previewTicket.value = ticket
}

function closePreview() {
  previewTicket.value = null
}

function formatDate(value) {
  if (!value) return ''

  const date = new Date(value)

  return date.toLocaleString('zh-TW', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function cleanValue(value) {
  return value && value !== '-' && value !== '--' ? String(value).trim() : ''
}
</script>
