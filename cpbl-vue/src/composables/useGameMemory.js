import { ref } from 'vue'

const FAVORITE_KEY = 'cpbl_favorite_games'
const TICKET_KEY = 'cpbl_ticket_pocket'
const SUPPORT_KEY = 'cpbl_game_support'

function readStorageObject(key) {
  try {
    const data = JSON.parse(localStorage.getItem(key) || '{}')
    return data && typeof data === 'object' && !Array.isArray(data) ? data : {}
  } catch {
    return {}
  }
}

const favorites = ref(readStorageObject(FAVORITE_KEY))
const rawTickets = readStorageObject(TICKET_KEY)
const support = ref(readStorageObject(SUPPORT_KEY))

// 把舊版「單筆票夾物件」自動轉成新版「陣列」
function normalizeTickets(data) {
  const normalized = {}

  Object.keys(data).forEach(gameId => {
    const value = data[gameId]

    // 新版：已經是陣列
    if (Array.isArray(value)) {
      normalized[gameId] = value
      return
    }

    // 舊版：單一物件，轉成陣列
    if (value && typeof value === 'object') {
      normalized[gameId] = [
        {
          id: value.id || Date.now() + Number(gameId),
          gameId: value.gameId || Number(gameId),
          date: value.date || '',
          location: value.location || '',
          away: value.away || '',
          home: value.home || '',
          away_score: value.away_score || '',
          home_score: value.home_score || '',
          status: value.status || '',
          note: value.note || '',
          image: value.image || '',
          createdAt: value.createdAt || value.updatedAt || new Date().toISOString()
        }
      ]
    }
  })

  return normalized
}

const tickets = ref(normalizeTickets(rawTickets))

// 存一次，把舊格式正式更新成新格式
localStorage.setItem(TICKET_KEY, JSON.stringify(tickets.value))

function saveFavorites() {
  localStorage.setItem(FAVORITE_KEY, JSON.stringify(favorites.value))
}

function saveTickets() {
  localStorage.setItem(TICKET_KEY, JSON.stringify(tickets.value))
}

function saveSupport() {
  localStorage.setItem(SUPPORT_KEY, JSON.stringify(support.value))
}

export function useGameMemory() {
  function isFavorite(gameId) {
    return !!favorites.value[gameId]
  }

  function toggleFavorite(game) {
    const id = game.id

    if (favorites.value[id]) {
      delete favorites.value[id]
    } else {
      favorites.value[id] = {
        gameId: game.id,
        date: game.date,
        location: game.location,
        away: game.away,
        home: game.home,
        away_score: game.away_score,
        home_score: game.home_score,
        status: game.status,
        createdAt: new Date().toISOString()
      }
    }

    favorites.value = { ...favorites.value }
    saveFavorites()
  }

  function hasTicket(gameId) {
    return Array.isArray(tickets.value[gameId]) && tickets.value[gameId].length > 0
  }

  function getTickets(gameId) {
    const value = tickets.value[gameId]

    if (Array.isArray(value)) {
      return value
    }

    return []
  }

  function getTicketCount(gameId) {
    return getTickets(gameId).length
  }

  function getAllTickets() {
    return Object.values(tickets.value)
      .flatMap(value => Array.isArray(value) ? value : [])
      .sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0))
  }

  function addTicket(game, payload) {
    const gameId = game.id

    if (!Array.isArray(tickets.value[gameId])) {
      tickets.value[gameId] = []
    }

    tickets.value[gameId].push({
      id: Date.now(),
      gameId: game.id,
      date: game.date,
      location: game.location,
      away: game.away,
      home: game.home,
      away_score: game.away_score,
      home_score: game.home_score,
      status: game.status,
      note: payload.note || '',
      image: payload.image || '',
      createdAt: new Date().toISOString()
    })

    tickets.value = { ...tickets.value }
    saveTickets()
  }

  function removeTicket(gameId, ticketId) {
    if (!Array.isArray(tickets.value[gameId])) return

    tickets.value[gameId] = tickets.value[gameId].filter(ticket => ticket.id !== ticketId)

    if (tickets.value[gameId].length === 0) {
      delete tickets.value[gameId]
    }

    tickets.value = { ...tickets.value }
    saveTickets()
  }

  function getSupportStats(gameId) {
    const current = support.value[gameId] || {}
    return {
      away: Number(current.away || 0),
      home: Number(current.home || 0)
    }
  }

  function getSupportChoice(gameId) {
    return support.value[gameId]?.choice || ''
  }

  function supportTeam(game, side) {
    const gameId = game.id
    const current = support.value[gameId] || { away: 0, home: 0, choice: '' }
    const previous = current.choice

    if (previous === side) {
      current[side] = Math.max(0, Number(current[side] || 0) - 1)
      current.choice = ''
    } else {
      if (previous) current[previous] = Math.max(0, Number(current[previous] || 0) - 1)
      current[side] = Number(current[side] || 0) + 1
      current.choice = side
    }

    support.value = {
      ...support.value,
      [gameId]: current
    }
    saveSupport()
  }

  return {
    favorites,
    tickets,
    support,
    isFavorite,
    toggleFavorite,
    hasTicket,
    getTickets,
    getTicketCount,
    getAllTickets,
    addTicket,
    removeTicket,
    getSupportStats,
    getSupportChoice,
    supportTeam
  }
}
