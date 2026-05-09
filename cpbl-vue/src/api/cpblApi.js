export const API_BASE = 'http://127.0.0.1:5000/api'

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
    const search = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') search.set(key, value)
    })
    const qs = search.toString()
    return request(`/games${qs ? `?${qs}` : ''}`)
  },

  getGameDetail(id) {
    return request(`/game/detail/${id}`)
  },

  getNews() {
    return request('/news')
  },

  getStandings() {
    return request('/get_standings')
  },

  updateToday() {
    return request('/update/today')
  },

  updateMonth(month) {
    return request(`/update/month?m=${month}`)
  },

  updateStandings() {
    return request('/update/standings')
  },

  getPlayerPool() {
    return request('/get_player_pool')
  }
}
