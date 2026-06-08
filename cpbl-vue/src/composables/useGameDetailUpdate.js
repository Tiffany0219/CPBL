function validText(value) {
  return value !== undefined && value !== null && value !== '' && value !== '-' && value !== '--'
}

function firstValue(values) {
  return Array.isArray(values) && validText(values[0]) ? String(values[0]) : ''
}

export function mergeGameWithDetail(game = {}, detail = {}) {
  const awayScore = firstValue(detail.away_rhe)
  const homeScore = firstValue(detail.home_rhe)
  const hasLineScore = awayScore || homeScore || (Array.isArray(detail.away_line) && detail.away_line.length)

  return {
    ...game,
    away_score: awayScore || game.away_score,
    home_score: homeScore || game.home_score,
    away_pitcher: detail.away_pitcher || game.away_pitcher,
    home_pitcher: detail.home_pitcher || game.home_pitcher,
    winning_pitcher: detail.winning_pitcher || game.winning_pitcher,
    losing_pitcher: detail.losing_pitcher || game.losing_pitcher,
    save_pitcher: detail.save_pitcher || game.save_pitcher,
    mvp: detail.mvp || game.mvp,
    mvp_team: detail.mvp_team || game.mvp_team,
    mvp_note: detail.mvp_note || game.mvp_note,
    status: hasLineScore && game.status !== 'LIVE' ? 'FINISH' : game.status,
    game_time: hasLineScore && game.status !== 'LIVE' ? 'Final' : game.game_time
  }
}

export function applyGameDetailUpdate(gamesRef, event) {
  const { id, detail } = event?.detail || {}
  if (!id || !detail || !Array.isArray(gamesRef.value)) return

  gamesRef.value = gamesRef.value.map(game =>
    String(game.id) === String(id) ? mergeGameWithDetail(game, detail) : game
  )
}

export async function hydrateMissingGameDetails(gamesRef, cpblApi, options = {}) {
  if (!Array.isArray(gamesRef.value)) return []

  const targetDate = options.date || ''
  const limit = Number(options.limit || 4)
  const candidates = gamesRef.value
    .filter(game => (!targetDate || game.date === targetDate) && needsDetailHydration(game))
    .slice(0, limit)

  const hydrated = []

  for (const game of candidates) {
    try {
      const detail = await cpblApi.getGameDetail(game.id)
      gamesRef.value = gamesRef.value.map(item =>
        String(item.id) === String(game.id) ? mergeGameWithDetail(item, detail) : item
      )
      hydrated.push({ id: game.id, detail })
    } catch (error) {
      console.warn('Game detail hydration failed', game.id, error)
    }
  }

  return hydrated
}

function needsDetailHydration(game = {}) {
  if (!isPastGame(game) && game.status !== 'FINISH') return false
  return !validText(game.away_pitcher) ||
    !validText(game.home_pitcher) ||
    !validText(game.mvp) ||
    !validText(game.away_score) ||
    !validText(game.home_score)
}

function isPastGame(game = {}) {
  const match = String(game.date || '').match(/^(\d{1,2})\/(\d{1,2})$/)
  if (!match) return false

  const now = new Date()
  const gameDate = new Date(now.getFullYear(), Number(match[1]) - 1, Number(match[2]), 23, 59, 59)
  return gameDate < now
}
