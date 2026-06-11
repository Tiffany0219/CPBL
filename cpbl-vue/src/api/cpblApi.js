export const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:5101/api'

function buildQuery(params = {}) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, value)
  })
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

async function request(path, options = {}) {
  const headers = {
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
    ...(options.headers || {})
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `API Error ${res.status}`)
  }
  return res.json()
}

function postJson(path, data, token) {
  return request(path, {
    method: 'POST',
    body: JSON.stringify(data || {}),
    token
  })
}

export const cpblApi = {
  getHealth() {
    return request('/health')
  },

  askAi(messages, activePage, token) {
    return postJson('/ai/chat', {
      messages,
      active_page: activePage
    }, token)
  },

  register(username, password) {
    return postJson('/auth/register', { username, password })
  },

  login(username, password) {
    return postJson('/auth/login', { username, password })
  },

  getMe(token) {
    return request('/auth/me', { token })
  },

  updateMe(data, token) {
    return request('/auth/me', {
      method: 'PATCH',
      body: JSON.stringify(data || {}),
      token
    })
  },

  getProfile(token) {
    return request('/profile', { token })
  },

  claimDailyReward(token) {
    return postJson('/rewards/daily', {}, token)
  },

  buyPointPack(packType, token) {
    return postJson('/shop/packs', { pack_type: packType }, token)
  },

  getUserCards(token) {
    return request('/cards', { token })
  },

  saveUserCard(card, token) {
    return postJson('/cards', card, token)
  },

  removeUserCard(name, token) {
    return request(`/cards/${encodeURIComponent(name)}`, { method: 'DELETE', token })
  },

  clearUserCards(token) {
    return request('/cards', { method: 'DELETE', token })
  },

  convertUserCard(name, count, token) {
    return postJson(`/cards/${encodeURIComponent(name)}/convert`, { count }, token)
  },

  convertDuplicateCards(token) {
    return postJson('/cards/convert-duplicates', {}, token)
  },

  getLineup(token) {
    return request('/lineup', { token })
  },

  saveLineup(slots, token) {
    return request('/lineup', {
      method: 'PUT',
      body: JSON.stringify({ slots }),
      token
    })
  },

  getUserTickets(token, gameId) {
    return request(`/tickets${buildQuery({ game_id: gameId })}`, { token })
  },

  saveUserTicket(game, ticket, token) {
    return postJson('/tickets', { game, ...ticket }, token)
  },

  removeUserTicket(ticketId, token) {
    return request(`/tickets/${ticketId}`, { method: 'DELETE', token })
  },

  getGames(params = {}) {
    return request(`/games${buildQuery(params)}`)
  },

  getGameDetail(id) {
    return request(`/game/detail/${id}`)
  },

  getNews(params = {}) {
    return request(`/get_news${buildQuery(params)}`)
  },

  getVenueWeather(params = {}) {
    return request(`/weather/venue${buildQuery(params)}`)
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

  updateMonth(month, year) {
    return request(`/update/month${buildQuery({ m: month, year })}`)
  },

  updateSchedule(params = {}) {
    return request(`/update/schedule${buildQuery(params)}`)
  },

  updateGameExtras(params = {}) {
    return request(`/update/game_extras${buildQuery(params)}`)
  },

  updateStandings() {
    return request('/update/standings')
  },

  getSyncStatus() {
    return request('/sync/status')
  },

  getPlayerPool() {
    return request('/get_player_pool')
  },

  initPlayerPool() {
    return request('/init_pool')
  },

  fuseUserCards(materials, slots, token) {
    return postJson('/cards/fuse', { materials, slots }, token)
  }
}
