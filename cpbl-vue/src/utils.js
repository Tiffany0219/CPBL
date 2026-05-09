export function getTodayMMDD() {
  const now = new Date()
  return `${String(now.getMonth() + 1).padStart(2, '0')}/${String(now.getDate()).padStart(2, '0')}`
}

export function getWeekdayStr(dateStr, year = 2026) {
  if (!dateStr || !dateStr.includes('/')) return ''
  const [m, d] = dateStr.split('/')
  const date = new Date(year, Number(m) - 1, Number(d))
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  return `星期${weekdays[date.getDay()]}`
}

export function groupBy(list, keyGetter) {
  return list.reduce((acc, item) => {
    const key = keyGetter(item)
    if (!acc[key]) acc[key] = []
    acc[key].push(item)
    return acc
  }, {})
}

export const TEAM_LOGOS = {
  '中信兄弟': '/static/image/teams/brothers.png',
  '味全龍': '/static/image/teams/dragons.png',
  '樂天桃猿': '/static/image/teams/monkeys.png',
  '統一7-ELEVEn獅': '/static/image/teams/lions.png',
  '富邦悍將': '/static/image/teams/guardians.png',
  '台鋼雄鷹': '/static/image/teams/hawks.png'
}
