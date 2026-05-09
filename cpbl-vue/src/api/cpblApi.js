export const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:5000/api'

function buildQuery(params = {}) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, value)
  })
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `API Error ${res.status}`)
  }
  return res.json()
}

export const cpblApi = {
  getGames(params = {}) {
    return request(`/games${buildQuery(params)}`)
  },

  getGameDetail(id) {
    return request(`/game/detail/${id}`)
  },

  getNews(params = {}) {
    return request(`/get_news${buildQuery(params)}`)
  },

  getStandings() {
    return request('/get_standings')
  },

  getTopStats(params = {}) {
    return request(`/top_stats${buildQuery(params)}`)
  },

  updateToday() {
    return request('/update/today')
  },

  updateMonth(month) {
    return request(`/update/month?m=${month}`)
  },

  updateSchedule() {
    return request('/update/schedule')
  },

  updateStandings() {
    return request('/update/standings')
  },

  getPlayerPool() {
    return request('/get_player_pool')
  },

  initPlayerPool() {
    return request('/init_pool')
  }
}
