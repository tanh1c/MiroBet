<template>
  <div class="mirobet-view">
    <!-- Header -->
    <div class="header">
      <h1>🎯 MiroBet</h1>
      <p class="subtitle">Swarm Intelligence Sports Betting · NBA · Consensus Voting</p>
    </div>

    <!-- Prediction Form -->
    <div class="predict-section">
      <h2>Predict a Game</h2>
      <div class="predict-form">
        <div class="form-row">
          <label>
            Home Team
            <input v-model="homeTeam" placeholder="e.g. LAL" />
          </label>
          <span class="at">@</span>
          <label>
            Away Team
            <input v-model="awayTeam" placeholder="e.g. BOS" />
          </label>
          <label>
            Season
            <select v-model="season">
              <option value="2024-25">2024-25</option>
              <option value="2023-24">2023-24</option>
              <option value="2022-23">2022-23</option>
            </select>
          </label>
        </div>
        <button class="btn-predict" @click="runPrediction" :disabled="loading">
          {{ loading ? 'Running 64 agents...' : '🎲 Run MiroFish Consensus' }}
        </button>
        <p v-if="error" class="error">{{ error }}</p>
      </div>
    </div>

    <!-- Prediction Result -->
    <div v-if="result" class="result-section">
      <PredictionCard
        :homeTeam="homeTeam"
        :awayTeam="awayTeam"
        :consensus="result.consensus"
        :kelly="result.kelly"
        :signal="result.signal"
        :confidence="result.confidence.moneyline"
      />
    </div>

    <!-- Backtest Section -->
    <div class="backtest-section">
      <h2>Backtest</h2>
      <div class="backtest-form">
        <label>
          Season
          <select v-model="backtestSeason">
            <option value="2024-25">2024-25</option>
            <option value="2023-24">2023-24</option>
            <option value="2022-23">2022-23</option>
          </select>
        </label>
        <button class="btn-backtest" @click="runBacktest" :disabled="backtestLoading">
          {{ backtestLoading ? 'Running backtest...' : '▶ Run Backtest' }}
        </button>
      </div>

      <!-- Backtest Results -->
      <div v-if="backtestResult" class="backtest-results">
        <div class="metrics-grid">
          <div class="metric">
            <span class="metric-value">{{ backtestResult.total_games }}</span>
            <span class="metric-label">Total Games</span>
          </div>
          <div class="metric" :class="resultClass(backtestResult.win_rate)">
            <span class="metric-value">{{ ((backtestResult.win_rate || 0) * 100).toFixed(1) }}%</span>
            <span class="metric-label">Win Rate</span>
          </div>
          <div class="metric" :class="resultClass(backtestResult.roi)">
            <span class="metric-value">{{ ((backtestResult.roi || 0) * 100).toFixed(1) }}%</span>
            <span class="metric-label">ROI</span>
          </div>
          <div class="metric">
            <span class="metric-value">{{ backtestResult.total_bets }}</span>
            <span class="metric-label">Bets Made</span>
          </div>
          <div class="metric">
            <span class="metric-value">{{ ((backtestResult.avg_edge || 0) * 100).toFixed(1) }}%</span>
            <span class="metric-label">Avg Edge</span>
          </div>
          <div class="metric">
            <span class="metric-value">{{ backtestResult.status }}</span>
            <span class="metric-label">Status</span>
          </div>
        </div>

        <!-- Top edge bets -->
        <div v-if="backtestResult.edge_per_bet && backtestResult.edge_per_bet.length" class="top-bets">
          <h3>Top Edge Bets</h3>
          <table>
            <thead>
              <tr>
                <th>Game</th>
                <th>Edge</th>
                <th>Kelly</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in backtestResult.edge_per_bet" :key="item.game_id">
                <td>{{ item.game_id }}</td>
                <td class="positive">+{{ ((item.edge || 0) * 100).toFixed(1) }}%</td>
                <td>{{ item.kelly_pct || 'N/A' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { mirobetApi } from '@/api/mirobet'
import PredictionCard from '@/components/PredictionCard.vue'

export default {
  name: 'MiroBetView',
  components: { PredictionCard },
  data() {
    return {
      homeTeam: 'LAL',
      awayTeam: 'BOS',
      season: '2024-25',
      loading: false,
      error: null,
      result: null,
      backtestSeason: '2024-25',
      backtestLoading: false,
      backtestResult: null
    }
  },
  methods: {
    async runPrediction() {
      this.loading = true
      this.error = null
      this.result = null
      try {
        const res = await mirobetApi.predictGame({
          home_team: this.homeTeam,
          away_team: this.awayTeam,
          season: this.season
        })
        if (res.data.success) {
          this.result = res.data.data
        } else {
          this.error = res.data.error || 'Unknown error'
        }
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },
    async runBacktest() {
      this.backtestLoading = true
      this.backtestResult = null
      try {
        const res = await mirobetApi.runBacktest(this.backtestSeason)
        if (res.data.success) {
          this.backtestResult = res.data.data
        } else {
          this.backtestResult = { status: 'error: ' + (res.data.error || 'unknown') }
        }
      } catch (e) {
        this.backtestResult = { status: 'error: ' + e.message }
      } finally {
        this.backtestLoading = false
      }
    },
    resultClass(value) {
      if (value > 0.05) return 'positive'
      if (value < -0.05) return 'negative'
      return 'neutral'
    }
  }
}
</script>

<style scoped>
.mirobet-view {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px;
  color: #e2e8f0;
}
.header { text-align: center; margin-bottom: 32px; }
.header h1 { font-size: 36px; margin: 0; color: #fff; }
.subtitle { color: #888; margin-top: 4px; font-size: 14px; }

.predict-section, .backtest-section {
  background: #0f0f1f;
  border: 1px solid #2a2a4e;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
}
.predict-section h2, .backtest-section h2 { margin-top: 0; color: #fff; font-size: 18px; }

.form-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.form-row label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: #888; }
.form-row input, .form-row select {
  background: #1a1a2e;
  border: 1px solid #3a3a5e;
  border-radius: 8px;
  color: #fff;
  padding: 8px 12px;
  font-size: 14px;
}
.at { font-size: 20px; color: #888; align-self: center; padding-bottom: 6px; }

.btn-predict, .btn-backtest {
  background: linear-gradient(135deg, #4ade80, #22d3ee);
  border: none;
  border-radius: 10px;
  color: #000;
  font-weight: 700;
  font-size: 14px;
  padding: 12px 24px;
  cursor: pointer;
  width: 100%;
}
.btn-predict:disabled, .btn-backtest:disabled { opacity: 0.6; cursor: not-allowed; }

.error { color: #f87171; margin-top: 12px; font-size: 13px; }

.result-section { margin-bottom: 24px; }

.backtest-form { display: flex; gap: 12px; align-items: flex-end; margin-bottom: 16px; }
.btn-backtest { width: auto; }

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.metric {
  background: #1a1a2e;
  border-radius: 10px;
  padding: 16px;
  text-align: center;
  border: 1px solid #2a2a4e;
}
.metric-value { display: block; font-size: 24px; font-weight: 700; color: #fff; }
.metric-label { font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
.metric.positive .metric-value { color: #4ade80; }
.metric.negative .metric-value { color: #f87171; }

.top-bets h3 { color: #fff; font-size: 14px; margin-bottom: 8px; }
.top-bets table { width: 100%; border-collapse: collapse; font-size: 13px; }
.top-bets th { color: #888; text-align: left; padding: 6px 8px; border-bottom: 1px solid #2a2a4e; }
.top-bets td { padding: 6px 8px; border-bottom: 1px solid #1a1a2e; }
.top-bets .positive { color: #4ade80; font-weight: 600; }
</style>
