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

            <button
              class="ticket-design-btn"
              title="生成紀念票券"
              @click="generateTicketDesign(ticket)"
            >
              <i class="fa-solid fa-ticket"></i>
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

      <!-- 紀念票券預覽與下載 -->
      <div
        v-if="showDesignModal"
        class="ticket-image-viewer"
        @click="showDesignModal = false"
      >
        <div class="ticket-image-viewer-card lineup-share-modal" @click.stop>
          <button class="ticket-image-close" @click="showDesignModal = false">
            &times;
          </button>
          <p class="eyebrow" style="margin-top: 15px;">MEMORIAL TICKET</p>
          <h3>觀賽紀念票券</h3>
          
          <div style="padding: 10px; background: #0f172a; border-radius: 12px; margin: 0 16px 8px;">
            <img
              :src="designImage"
              alt="紀念票券"
              style="width: 100%; border-radius: 8px; display: block;"
            />
          </div>

          <div style="padding: 14px 18px 18px; display: flex; justify-content: center; gap: 12px;">
            <button class="btn-primary" @click="downloadDesignTicket" style="margin: 0;">
              <i class="fa-solid fa-download"></i>
              下載票券圖片
            </button>
            <button class="btn-soft" @click="showDesignModal = false" style="margin: 0;">
              關閉
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, inject, ref, watch } from 'vue'
import ticketStadiumBg from '../assets/ticket-stadium-bg.jpeg'

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

const showDesignModal = ref(false)
const designImage = ref('')

async function generateTicketDesign(ticket) {
  const canvas = document.createElement('canvas')
  canvas.width = 1800
  canvas.height = 760
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const teamColors = {
    '中信兄弟': '#b9891d',
    '味全龍': '#b64235',
    '樂天桃猿': '#8f2f46',
    '統一7-ELEVEn獅': '#c56f2d',
    '統一7-11獅': '#c56f2d',
    '統一獅': '#c56f2d',
    '富邦悍將': '#2f6690',
    '台鋼雄鷹': '#2f7d68'
  }
  const teamEnglish = {
    '中信兄弟': 'CTBC BROTHERS',
    '味全龍': 'WEI CHUAN DRAGONS',
    '樂天桃猿': 'RAKUTEN MONKEYS',
    '統一7-ELEVEn獅': 'UNI-LIONS',
    '統一7-11獅': 'UNI-LIONS',
    '統一獅': 'UNI-LIONS',
    '富邦悍將': 'FUBON GUARDIANS',
    '台鋼雄鷹': 'TSG HAWKS'
  }
  const homeTeam = props.game?.home || 'CPBL'
  const homeColor = teamColors[homeTeam] || '#111827'
  const awayTeam = props.game?.away || 'CPBL'
  const accentColor = teamColors[awayTeam] || homeColor
  const awayScore = cleanValue(props.game?.away_score) || '--'
  const homeScore = cleanValue(props.game?.home_score) || '--'
  const noteText = ticket.note || '這天我在現場見證精彩賽事！'
  const [image, stadiumBackground] = await Promise.all([
    ticket.image ? loadCanvasImage(ticket.image) : Promise.resolve(null),
    loadCanvasImage(ticketStadiumBg)
  ])
  const stubX = 510

  ctx.fillStyle = '#0b1f33'
  ctx.fillRect(0, 0, 1800, 760)
  drawTicketShadow(ctx)

  ctx.save()
  roundRect(ctx, 32, 32, 1736, 694, 34)
  ctx.clip()

  const paperGradient = ctx.createLinearGradient(520, 60, 1760, 700)
  paperGradient.addColorStop(0, '#fff8e9')
  paperGradient.addColorStop(0.58, '#fff2dc')
  paperGradient.addColorStop(1, '#f7dfb9')
  ctx.fillStyle = paperGradient
  ctx.fillRect(32, 32, 1736, 694)
  drawFadedStadiumBackground(ctx, stadiumBackground, stubX, 44, 1768 - stubX, 670)
  drawPaperTexture(ctx, 32, 32, 1736, 694)

  const stubGradient = ctx.createLinearGradient(32, 32, stubX, 726)
  stubGradient.addColorStop(0, '#0b2a42')
  stubGradient.addColorStop(0.56, '#071e30')
  stubGradient.addColorStop(1, '#061827')
  ctx.fillStyle = stubGradient
  ctx.fillRect(32, 32, stubX - 32, 694)
  drawPaperTexture(ctx, 32, 32, stubX - 32, 694, 0.08)

  ctx.fillStyle = rgbaFromHex(homeColor, 0.1)
  ctx.fillRect(stubX, 32, 1768 - stubX, 12)
  ctx.fillStyle = rgbaFromHex(accentColor, 0.1)
  ctx.fillRect(stubX, 714, 1768 - stubX, 12)

  ctx.restore()

  ctx.strokeStyle = '#d6a451'
  ctx.lineWidth = 3
  roundRect(ctx, 32, 32, 1736, 694, 34)
  ctx.stroke()
  ctx.strokeStyle = 'rgba(255, 248, 234, 0.34)'
  ctx.lineWidth = 1.5
  roundRect(ctx, 42, 42, 1716, 674, 28)
  ctx.stroke()

  drawPerforation(ctx, stubX, 44, 708)

  ctx.fillStyle = '#0b1f33'
  ctx.beginPath()
  ctx.arc(stubX, 32, 36, 0, Math.PI, false)
  ctx.fill()
  ctx.beginPath()
  ctx.arc(stubX, 726, 36, Math.PI, 0, false)
  ctx.fill()

  ctx.save()
  ctx.translate(112, 380)
  ctx.rotate(-Math.PI / 2)
  ctx.fillStyle = '#d7a650'
  ctx.font = '700 31px Georgia, serif'
  ctx.textAlign = 'center'
  ctx.fillText('★ ADMIT ONE ★', 0, 0)
  ctx.restore()

  ctx.save()
  ctx.translate(200, 380)
  ctx.rotate(-Math.PI / 2)
  ctx.fillStyle = '#fff8ea'
  ctx.font = '900 78px sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText('ENTRY PASS', 0, 0)
  ctx.restore()

  const barcodeX = 292
  const barcodeY = 86
  const barcodeW = 154
  const barcodeH = 535
  ctx.fillStyle = '#fff8ea'
  roundRect(ctx, barcodeX - 16, barcodeY - 18, barcodeW + 32, barcodeH + 70, 18)
  ctx.fill()
  ctx.strokeStyle = '#d6a451'
  ctx.lineWidth = 3
  roundRect(ctx, barcodeX - 16, barcodeY - 18, barcodeW + 32, barcodeH + 70, 18)
  ctx.stroke()
  drawBarcode(ctx, barcodeX, barcodeY, barcodeW, barcodeH)

  ctx.fillStyle = '#0b1f33'
  ctx.font = '700 20px sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText(`No. CPBL-${props.game?.id || 0}-${ticket.id || 0}`, barcodeX + barcodeW / 2, barcodeY + barcodeH + 42)

  ctx.textAlign = 'center'
  ctx.fillStyle = '#0b1f33'
  ctx.font = '900 34px sans-serif'
  ctx.fillText('CHINESE PROFESSIONAL BASEBALL LEAGUE', 1120, 92)

  ctx.strokeStyle = '#b07a2d'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(665, 82)
  ctx.lineTo(780, 82)
  ctx.moveTo(1460, 82)
  ctx.lineTo(1590, 82)
  ctx.stroke()

  drawRibbon(ctx, 805, 110, 570, 50, '#b07a2d')
  ctx.fillStyle = '#fff8ea'
  ctx.font = '900 28px Georgia, serif'
  ctx.fillText('★  OFFICIAL MEMORIAL PASS  ★', 1090, 144)

  const matchupText = `${awayTeam} VS ${homeTeam}`
  ctx.fillStyle = '#0b1f33'
  fitText(ctx, matchupText, 1110, 258, 920, '900', 88, 56)

  ctx.fillStyle = '#6d6253'
  ctx.font = '900 31px Georgia, serif'
  ctx.fillText(`${teamEnglish[awayTeam] || awayTeam}  VS  ${teamEnglish[homeTeam] || homeTeam}`, 1110, 312)

  drawScoreBoard(ctx, 625, 346, 470, 190, awayTeam, homeTeam, awayScore, homeScore)

  ctx.textAlign = 'left'
  ctx.fillStyle = '#0b1f33'
  ctx.font = '900 29px sans-serif'
  const infoIconX = 1150
  const infoTextX = 1218
  const dateY = 392
  const venueY = 467
  drawSmallIconBox(ctx, infoIconX, dateY - 35, 'calendar')
  ctx.fillText(`DATE: ${props.game?.date || '未知'}`, infoTextX, dateY)
  drawSmallIconBox(ctx, infoIconX, venueY - 35, 'venue')
  ctx.fillText(`VENUE: ${props.game?.location || '未知球場'}`, infoTextX, venueY)

  drawPolaroid(ctx, image, 1452, 380, 255, 278)

  const memoX = 585
  const memoY = 565
  const memoW = 835
  const memoH = 132
  ctx.fillStyle = 'rgba(255, 249, 238, 0.88)'
  roundRect(ctx, memoX, memoY, memoW, memoH, 14)
  ctx.fill()
  ctx.strokeStyle = 'rgba(176, 122, 45, 0.56)'
  ctx.lineWidth = 2
  roundRect(ctx, memoX, memoY, memoW, memoH, 14)
  ctx.stroke()

  ctx.fillStyle = 'rgba(176, 122, 45, 0.72)'
  ctx.font = '900 62px Georgia, serif'
  ctx.fillText('“', memoX + 62, memoY + 76)
  ctx.fillText('”', memoX + memoW - 112, memoY + 101)

  ctx.fillStyle = '#0b1f33'
  ctx.font = '900 34px sans-serif'
  ctx.textAlign = 'left'
  wrapText(ctx, noteText, memoX + 145, memoY + 76, memoW - 260, 40)
  ctx.strokeStyle = 'rgba(176, 122, 45, 0.42)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(memoX + 140, memoY + 106)
  ctx.lineTo(memoX + memoW - 140, memoY + 106)
  ctx.stroke()

  designImage.value = canvas.toDataURL('image/png')
  showDesignModal.value = true
}

function downloadDesignTicket() {
  if (!designImage.value) return
  const link = document.createElement('a')
  const cleanAway = props.game?.away || 'CPBL'
  const cleanHome = props.game?.home || 'CPBL'
  link.download = `CPBL-Ticket-${props.game?.date?.replace(/\//g, '-') || ''}-${cleanAway}-vs-${cleanHome}.png`
  link.href = designImage.value
  link.click()
}

function roundRect(ctx, x, y, width, height, radius) {
  ctx.beginPath()
  ctx.moveTo(x + radius, y)
  ctx.lineTo(x + width - radius, y)
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius)
  ctx.lineTo(x + width, y + height - radius)
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height)
  ctx.lineTo(x + radius, y + height)
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius)
  ctx.lineTo(x, y + radius)
  ctx.quadraticCurveTo(x, y, x + radius, y)
  ctx.closePath()
}

function rgbaFromHex(hex, alpha = 1) {
  const value = String(hex || '#0b1f33').replace('#', '')
  const normalized = value.length === 3
    ? value.split('').map(char => char + char).join('')
    : value.padEnd(6, '0').slice(0, 6)
  const r = parseInt(normalized.slice(0, 2), 16)
  const g = parseInt(normalized.slice(2, 4), 16)
  const b = parseInt(normalized.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function drawTicketShadow(ctx) {
  ctx.save()
  ctx.shadowColor = 'rgba(0, 0, 0, 0.34)'
  ctx.shadowBlur = 28
  ctx.shadowOffsetY = 18
  ctx.fillStyle = '#0b1f33'
  roundRect(ctx, 32, 32, 1736, 694, 34)
  ctx.fill()
  ctx.restore()
}

function drawPaperTexture(ctx, x, y, width, height, opacity = 0.11) {
  ctx.save()
  ctx.globalAlpha = opacity
  for (let i = 0; i < 900; i++) {
    const px = x + Math.random() * width
    const py = y + Math.random() * height
    const shade = Math.random() > 0.5 ? '#6d4b20' : '#ffffff'
    ctx.fillStyle = shade
    ctx.fillRect(px, py, 1.2, 1.2)
  }
  ctx.restore()
}

function drawBaseballWatermark(ctx, cx, cy, r) {
  ctx.save()
  ctx.globalAlpha = 0.08
  ctx.strokeStyle = '#8b6a39'
  ctx.lineWidth = 10
  ctx.beginPath()
  ctx.arc(cx, cy, r, 0, Math.PI * 2)
  ctx.stroke()
  ctx.lineWidth = 6
  ctx.beginPath()
  ctx.arc(cx - r * 0.68, cy, r * 0.82, -Math.PI / 3, Math.PI / 3)
  ctx.stroke()
  ctx.beginPath()
  ctx.arc(cx + r * 0.68, cy, r * 0.82, Math.PI * 0.66, Math.PI * 1.34)
  ctx.stroke()
  ctx.restore()
}

function drawFadedStadiumBackground(ctx, image, x, y, width, height) {
  if (!image) return
  ctx.save()
  ctx.globalAlpha = 0.34
  drawCoveredImage(ctx, image, x, y, width, height)
  ctx.globalAlpha = 1

  const wash = ctx.createLinearGradient(x, y, x + width, y + height)
  wash.addColorStop(0, 'rgba(255, 248, 234, 0.68)')
  wash.addColorStop(0.5, 'rgba(255, 242, 220, 0.58)')
  wash.addColorStop(1, 'rgba(247, 223, 185, 0.5)')
  ctx.fillStyle = wash
  ctx.fillRect(x, y, width, height)

  ctx.fillStyle = 'rgba(255, 248, 234, 0.08)'
  ctx.fillRect(x, y, width, height)
  ctx.restore()
}

function drawPerforation(ctx, x, top, bottom) {
  ctx.save()
  ctx.strokeStyle = 'rgba(11, 31, 51, 0.26)'
  ctx.setLineDash([10, 12])
  ctx.beginPath()
  ctx.moveTo(x, top + 18)
  ctx.lineTo(x, bottom - 18)
  ctx.stroke()
  ctx.setLineDash([])

  ctx.fillStyle = '#0b1f33'
  for (let y = top + 28; y <= bottom - 28; y += 26) {
    ctx.beginPath()
    ctx.arc(x, y, 8, 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.restore()
}

function drawBarcode(ctx, x, y, width, height) {
  ctx.save()
  ctx.fillStyle = '#0b1f33'
  let currentY = y + 10
  while (currentY < y + height - 10) {
    const lineH = Math.random() > 0.36 ? 5 : 2
    const spacing = Math.random() > 0.46 ? 5 : 3
    ctx.fillRect(x + 10, currentY, width - 20, lineH)
    currentY += lineH + spacing
  }
  ctx.restore()
}

function drawRibbon(ctx, x, y, width, height, color) {
  ctx.save()
  ctx.fillStyle = color
  ctx.beginPath()
  ctx.moveTo(x, y)
  ctx.lineTo(x + width, y)
  ctx.lineTo(x + width - 24, y + height / 2)
  ctx.lineTo(x + width, y + height)
  ctx.lineTo(x, y + height)
  ctx.lineTo(x + 24, y + height / 2)
  ctx.closePath()
  ctx.fill()
  ctx.restore()
}

function fitText(ctx, text, x, y, maxWidth, weight = '900', maxSize = 72, minSize = 34) {
  let size = maxSize
  do {
    ctx.font = `${weight} ${size}px sans-serif`
    size -= 2
  } while (ctx.measureText(text).width > maxWidth && size >= minSize)
  ctx.textAlign = 'center'
  ctx.fillText(text, x, y)
}

function drawScoreBoard(ctx, x, y, width, height, awayTeam, homeTeam, awayScore, homeScore) {
  ctx.save()
  ctx.fillStyle = '#0b1f33'
  roundRect(ctx, x, y, width, height, 14)
  ctx.fill()
  ctx.strokeStyle = '#b07a2d'
  ctx.lineWidth = 3
  roundRect(ctx, x, y, width, height, 14)
  ctx.stroke()

  ctx.fillStyle = '#0b1f33'
  ctx.fillRect(x + 14, y + 14, width - 28, 48)
  ctx.fillStyle = '#d6a451'
  ctx.font = '900 26px sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText('★  FINAL SCORE  ★', x + width / 2, y + 47)

  const rowY = y + 62
  const rowH = 52
  const scoreW = 108
  const teamTextOffset = 36
  const scoreTextOffset = 44
  ctx.fillStyle = 'rgba(255, 248, 234, 0.94)'
  ctx.fillRect(x + 14, rowY, width - 28, rowH * 2)
  ctx.strokeStyle = 'rgba(176, 122, 45, 0.4)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(x + 14, rowY + rowH)
  ctx.lineTo(x + width - 14, rowY + rowH)
  ctx.moveTo(x + width - scoreW - 14, rowY)
  ctx.lineTo(x + width - scoreW - 14, rowY + rowH * 2)
  ctx.stroke()

  ctx.fillStyle = '#b07a2d'
  ctx.fillRect(x + width - scoreW - 14, rowY, scoreW, rowH * 2)
  ctx.fillStyle = '#0b1f33'
  ctx.font = '900 36px sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText(awayTeam, x + (width - scoreW) / 2, rowY + teamTextOffset)
  ctx.fillText(homeTeam, x + (width - scoreW) / 2, rowY + rowH + teamTextOffset)
  ctx.fillStyle = '#fff8ea'
  ctx.font = '900 50px sans-serif'
  ctx.fillText(String(awayScore), x + width - scoreW / 2 - 14, rowY + scoreTextOffset)
  ctx.fillText(String(homeScore), x + width - scoreW / 2 - 14, rowY + rowH + scoreTextOffset)
  ctx.restore()
}

function drawSmallIconBox(ctx, x, y, type) {
  ctx.save()
  ctx.fillStyle = 'rgba(176, 122, 45, 0.18)'
  roundRect(ctx, x, y, 46, 46, 10)
  ctx.fill()
  ctx.strokeStyle = '#b07a2d'
  ctx.lineWidth = 3

  if (type === 'calendar') {
    ctx.strokeRect(x + 10, y + 13, 26, 24)
    ctx.beginPath()
    ctx.moveTo(x + 10, y + 21)
    ctx.lineTo(x + 36, y + 21)
    ctx.moveTo(x + 17, y + 8)
    ctx.lineTo(x + 17, y + 16)
    ctx.moveTo(x + 29, y + 8)
    ctx.lineTo(x + 29, y + 16)
    ctx.stroke()
  } else {
    ctx.beginPath()
    ctx.arc(x + 23, y + 20, 18, Math.PI, Math.PI * 2)
    ctx.lineTo(x + 39, y + 36)
    ctx.lineTo(x + 7, y + 36)
    ctx.closePath()
    ctx.stroke()
    ctx.beginPath()
    ctx.arc(x + 23, y + 20, 5, 0, Math.PI * 2)
    ctx.stroke()
  }
  ctx.restore()
}

function loadCanvasImage(src) {
  return new Promise((resolve) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => resolve(img)
    img.onerror = () => resolve(null)
    img.src = src
  })
}

function drawCoveredImage(ctx, image, x, y, width, height) {
  const scale = Math.max(width / image.width, height / image.height)
  const sw = width / scale
  const sh = height / scale
  const sx = (image.width - sw) / 2
  const sy = (image.height - sh) / 2
  ctx.drawImage(image, sx, sy, sw, sh, x, y, width, height)
}

function drawPolaroid(ctx, image, x, y, width, height) {
  ctx.save()
  ctx.translate(x + width / 2, y + height / 2)
  ctx.rotate(0.08)
  ctx.translate(-width / 2, -height / 2)
  ctx.shadowColor = 'rgba(11, 31, 51, 0.25)'
  ctx.shadowBlur = 22
  ctx.shadowOffsetY = 12
  ctx.fillStyle = '#fffaf0'
  roundRect(ctx, 0, 0, width, height, 4)
  ctx.fill()
  ctx.shadowColor = 'transparent'

  const imageX = 18
  const imageY = 18
  const imageW = width - 36
  const imageH = height - 72
  if (image) {
    drawCoveredImage(ctx, image, imageX, imageY, imageW, imageH)
  } else {
    drawBaseballLogo(ctx, width / 2, imageY + imageH / 2, 58)
  }

  ctx.fillStyle = '#0b1f33'
  ctx.font = '900 21px Georgia, serif'
  ctx.textAlign = 'center'
  ctx.fillText('★  GAME MEMORY  ★', width / 2, height - 22)

  ctx.fillStyle = 'rgba(176, 122, 45, 0.45)'
  roundRect(ctx, width / 2 - 68, -20, 136, 34, 4)
  ctx.fill()
  ctx.restore()
}

function wrapText(ctx, text, x, y, maxWidth, lineHeight) {
  const words = text.split('')
  let line = ''
  let currentY = y

  for (let n = 0; n < words.length; n++) {
    const testLine = line + words[n]
    const metrics = ctx.measureText(testLine)
    const testWidth = metrics.width
    
    if (currentY > y + 70) {
      ctx.fillText(line.substring(0, Math.max(1, line.length - 2)) + '...', x, currentY)
      return
    }

    if (testWidth > maxWidth && n > 0) {
      ctx.fillText(line, x, currentY)
      line = words[n]
      currentY += lineHeight
    } else {
      line = testLine
    }
  }
  if (currentY <= y + 70) {
    ctx.fillText(line, x, currentY)
  }
}

function drawBaseballLogo(ctx, cx, cy, r) {
  ctx.save()
  ctx.fillStyle = '#f8fafc'
  ctx.beginPath()
  ctx.arc(cx, cy, r, 0, Math.PI * 2)
  ctx.fill()
  
  ctx.strokeStyle = '#cbd5e1'
  ctx.lineWidth = 2
  ctx.stroke()

  ctx.strokeStyle = '#ef4444'
  ctx.lineWidth = 1.5
  
  ctx.beginPath()
  ctx.arc(cx - r * 0.8, cy, r * 0.9, -Math.PI / 4, Math.PI / 4)
  ctx.stroke()

  ctx.beginPath()
  ctx.arc(cx + r * 0.8, cy, r * 0.9, Math.PI * 0.75, Math.PI * 1.25)
  ctx.stroke()
  ctx.restore()
}

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
    minute: '2-digit',
    hour12: true
  })
}

function cleanValue(value) {
  return value && value !== '-' && value !== '--' ? String(value).trim() : ''
}
</script>

<style scoped>
.ticket-design-btn {
  position: absolute;
  top: 10px;
  right: 90px;
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 50%;
  background: rgba(17, 24, 39, 0.72);
  color: #ffffff;
  cursor: pointer;
  transition: 0.18s ease;
  z-index: 3;
}

.ticket-design-btn:hover {
  background: #f59e0b;
  transform: scale(1.05);
}
</style>
