export const COLLECTION_KEY = 'my_cpbl_collection'

export const TEAMS = ['中信兄弟', '味全龍', '樂天桃猿', '統一7-ELEVEn獅', '富邦悍將', '台鋼雄鷹']

export const TEAM_COLORS = {
  中信兄弟: '#d8a900',
  味全龍: '#c8102e',
  樂天桃猿: '#7a0019',
  '統一7-ELEVEn獅': '#f58220',
  富邦悍將: '#004b8d',
  台鋼雄鷹: '#006847'
}

export function cleanPlayerName(playerOrName = '') {
  const value = typeof playerOrName === 'string' ? playerOrName : playerOrName?.name
  return (value || '未知球員').replace(/\*/g, '').trim()
}

export function playerInitials(playerOrName = '') {
  return cleanPlayerName(playerOrName).slice(0, 2) || '球員'
}

export function teamColor(team = '') {
  return TEAM_COLORS[team] || '#334155'
}

export function playerRarity(player = {}) {
  const explicit = String(player.rarity || '').toLowerCase()
  if (['common', 'rare', 'legend'].includes(explicit)) return explicit
  const name = cleanPlayerName(player)
  if (name === '頌恩') return 'legend'
  const score = Array.from(name).reduce((sum, char) => sum + char.charCodeAt(0), 0)
  if (score % 19 === 0) return 'legend'
  if (score % 5 === 0) return 'rare'
  return 'common'
}

export function rarityLabel(rarity = 'common') {
  return {
    common: '一般',
    rare: '稀有',
    legend: '傳說'
  }[rarity] || '一般'
}

export function normalizePlayer(player = {}, fallbackName = '') {
  return {
    name: cleanPlayerName(player.name || fallbackName),
    team: player.team || '',
    position: player.position || '',
    description: player.description || '',
    rarity: playerRarity(player),
    count: Number(player.count || 1)
  }
}

export function readCollectionMap() {
  try {
    const data = JSON.parse(localStorage.getItem(COLLECTION_KEY) || '{}')
    return data && typeof data === 'object' && !Array.isArray(data) ? data : {}
  } catch {
    return {}
  }
}

export function saveCollectionMap(collectionMap) {
  localStorage.setItem(COLLECTION_KEY, JSON.stringify(collectionMap || {}))
}

export function getCollectionList() {
  return Object.entries(readCollectionMap())
    .map(([name, player]) => normalizePlayer(player, name))
    .sort((a, b) => cleanPlayerName(a).localeCompare(cleanPlayerName(b), 'zh-Hant'))
}

export function addPlayerToCollection(player) {
  const key = cleanPlayerName(player)
  const collectionMap = readCollectionMap()
  const current = collectionMap[key]

  collectionMap[key] = current
    ? normalizePlayer({ ...current, count: Number(current.count || 1) + 1 }, key)
    : normalizePlayer({ ...player, count: 1 }, key)

  saveCollectionMap(collectionMap)
  return collectionMap[key]
}

export function removePlayerFromCollection(playerName) {
  const key = cleanPlayerName(playerName)
  const collectionMap = readCollectionMap()
  delete collectionMap[key]
  saveCollectionMap(collectionMap)
}

export function clearPlayerCollection() {
  saveCollectionMap({})
}
