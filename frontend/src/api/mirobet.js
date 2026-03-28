/**
 * MiroBet API client
 */
import api from './index'

const BASE = '/api/mirobet'

export const mirobetApi = {
  health() {
    return api.get(`${BASE}/health`)
  },

  predictGame({ home_team, away_team, season = '2024-25', game_date = '' }) {
    return api.post(`${BASE}/predict`, { home_team, away_team, season, game_date })
  },

  runBacktest(season) {
    return api.post(`${BASE}/backtest`, { season })
  },

  importOdds(filePath) {
    return api.post(`${BASE}/odds/import`, { file_path: filePath })
  }
}

export default mirobetApi
