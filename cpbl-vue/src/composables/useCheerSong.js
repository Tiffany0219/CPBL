import { cleanPlayerName } from './usePlayerCollection'

const DIRECT_ID_FIELDS = [
  'youtubeId',
  'youtube_id',
  'cheerYoutubeId',
  'cheer_youtube_id',
  'supportYoutubeId'
]

const DIRECT_URL_FIELDS = [
  'youtubeUrl',
  'youtube_url',
  'cheerYoutubeUrl',
  'cheer_youtube_url',
  'supportYoutubeUrl'
]

const CHEER_SONGS = {
  // 之後只要補上球員姓名與 YouTube ID，抽到該球員就會直接播放。
  // 例：王威晨: { youtubeId: '影片ID', title: '王威晨 應援曲' }
  '張育成': { youtubeId: 'ZdAvmv8cXvg', title: '張育成 應援曲' },
  '邦力多': { youtubeId: 'AlsnmZW8a_Q', title: '邦力多 應援曲' },
  '邦利多': { youtubeId: 'AlsnmZW8a_Q', title: '邦力多 應援曲' },
  '申皓瑋': { youtubeId: 'JPtvrSibDHU', title: '申皓瑋 應援曲' },
  '王勝偉': { youtubeId: '3qqY55FOblU', title: '王勝偉 應援曲' },
  '王念好': { youtubeId: 'Q8DgGgi0_nA', title: '王念好 應援曲' },
  '葉子霆': { youtubeId: 'z4FohkoIVLU', title: '葉子霆 應援曲' }
}

const CHEER_OVERRIDE_KEY = 'gobase_cheer_songs'

export function resolveCheerSong(player = {}) {
  const name = cleanPlayerName(player)
  const override = readCheerOverrides()[name] || {}
  const mapped = CHEER_SONGS[name] || {}
  const youtubeId = findYoutubeId(player) || override.youtubeId || mapped.youtubeId || extractYoutubeId(mapped.youtubeUrl)
  const title = override.title || mapped.title || player.cheerTitle || `${name} 應援曲`
  const query = `${player.team || 'CPBL'} ${name} 應援曲`

  return {
    title,
    youtubeId,
    hasVideo: Boolean(youtubeId),
    searchUrl: `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`
  }
}

export function youtubeEmbedUrl(youtubeId) {
  if (!youtubeId) return ''
  const params = new URLSearchParams({
    autoplay: '1',
    playsinline: '1',
    rel: '0',
    enablejsapi: '1'
  })
  return `https://www.youtube.com/embed/${youtubeId}?${params.toString()}`
}

export function saveCheerOverride(playerOrName, value) {
  const name = cleanPlayerName(playerOrName)
  const rawId = extractYoutubeId(value) || String(value || '').trim()
  const youtubeId = /^[a-zA-Z0-9_-]{6,}$/.test(rawId) ? rawId : ''
  if (!name || !youtubeId) return false

  const data = readCheerOverrides()
  data[name] = {
    youtubeId,
    title: `${name} 應援曲`
  }
  localStorage.setItem(CHEER_OVERRIDE_KEY, JSON.stringify(data))
  return true
}

export function readCheerOverrides() {
  try {
    const data = JSON.parse(localStorage.getItem(CHEER_OVERRIDE_KEY) || '{}')
    return data && typeof data === 'object' && !Array.isArray(data) ? data : {}
  } catch {
    return {}
  }
}

export function deleteCheerOverride(playerOrName) {
  const name = cleanPlayerName(playerOrName)
  if (!name) return false
  const data = readCheerOverrides()
  if (data[name]) {
    delete data[name]
    localStorage.setItem(CHEER_OVERRIDE_KEY, JSON.stringify(data))
    return true
  }
  return false
}

function findYoutubeId(player = {}) {
  for (const field of DIRECT_ID_FIELDS) {
    if (player[field]) return String(player[field]).trim()
  }

  for (const field of DIRECT_URL_FIELDS) {
    const id = extractYoutubeId(player[field])
    if (id) return id
  }

  return ''
}

export function extractYoutubeId(value = '') {
  const url = String(value || '').trim()
  if (!url) return ''

  const patterns = [
    /youtu\.be\/([a-zA-Z0-9_-]{6,})/,
    /youtube\.com\/watch\?v=([a-zA-Z0-9_-]{6,})/,
    /youtube\.com\/embed\/([a-zA-Z0-9_-]{6,})/,
    /youtube\.com\/shorts\/([a-zA-Z0-9_-]{6,})/
  ]

  for (const pattern of patterns) {
    const match = url.match(pattern)
    if (match?.[1]) return match[1]
  }

  return ''
}
