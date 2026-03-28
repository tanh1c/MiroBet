<template>
  <div class="prediction-card" :class="signalClass">
    <!-- Header -->
    <div class="card-header">
      <div class="teams">
        <span class="home-team">{{ homeTeam }}</span>
        <span class="vs">@</span>
        <span class="away-team">{{ awayTeam }}</span>
      </div>
      <span class="signal-badge" :class="signalClass">{{ signal }}</span>
    </div>

    <!-- Confidence bar -->
    <div class="confidence-bar">
      <div class="confidence-fill" :style="{ width: confidencePct + '%' }"></div>
    </div>

    <!-- Bet types -->
    <div class="bet-types">
      <!-- Moneyline -->
      <div class="bet-type" :class="{ highlighted: signal === 'HOME_ML' || signal === 'AWAY_ML' }">
        <span class="bet-label">Moneyline</span>
        <div class="prob-row">
          <span class="team-label">{{ homeTeam }} W:</span>
          <span class="prob-value">{{ consensus.moneyline.home_win | pct }}%</span>
          <span class="edge" :class="edgeClass(consensus.moneyline.edge)">
            {{ edgeStr(consensus.moneyline.edge) }}
          </span>
        </div>
        <div class="kelly-row" v-if="kelly.home_ml">
          <span class="kelly-label">Kelly:</span>
          <span class="kelly-value" :class="{ bet: kelly.home_ml.should_bet }">
            {{ kelly.home_ml.should_bet ? kelly.home_ml.kelly_pct + ' units' : 'NO BET' }}
          </span>
        </div>
      </div>

      <!-- Spread -->
      <div class="bet-type" :class="{ highlighted: signal === 'HOME_SPREAD' }">
        <span class="bet-label">Spread ({{ consensus.spread.line > 0 ? '+' : '' }}{{ consensus.spread.line }})</span>
        <div class="prob-row">
          <span class="team-label">{{ homeTeam }} Cover:</span>
          <span class="prob-value">{{ (consensus.spread.home_cover * 100).toFixed(0) }}%</span>
          <span class="edge" :class="edgeClass(consensus.spread.edge)">
            {{ edgeStr(consensus.spread.edge) }}
          </span>
        </div>
        <div class="kelly-row" v-if="kelly.home_spread">
          <span class="kelly-label">Kelly:</span>
          <span class="kelly-value" :class="{ bet: kelly.home_spread.should_bet }">
            {{ kelly.home_spread.should_bet ? kelly.home_spread.kelly_pct + ' units' : 'NO BET' }}
          </span>
        </div>
      </div>

      <!-- Over/Under -->
      <div class="bet-type" :class="{ highlighted: signal === 'OVER' || signal === 'UNDER' }">
        <span class="bet-label">O/U {{ consensus.over_under.line }}</span>
        <div class="prob-row">
          <span class="team-label">Over:</span>
          <span class="prob-value">{{ (consensus.over_under.over * 100).toFixed(0) }}%</span>
          <span class="edge" :class="edgeClass(consensus.over_under.edge)">
            {{ edgeStr(consensus.over_under.edge) }}
          </span>
        </div>
        <div class="kelly-row" v-if="kelly.over">
          <span class="kelly-label">Kelly:</span>
          <span class="kelly-value" :class="{ bet: kelly.over.should_bet }">
            {{ kelly.over.should_bet ? kelly.over.kelly_pct + ' units' : 'NO BET' }}
          </span>
        </div>
      </div>
    </div>

    <!-- Polymarket baseline -->
    <div class="baseline">
      <span class="baseline-label">Polymarket implied:</span>
      <span class="baseline-value">{{ (consensus.moneyline.polymarket_implied * 100).toFixed(0) }}%</span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PredictionCard',
  props: {
    homeTeam: { type: String, required: true },
    awayTeam: { type: String, required: true },
    consensus: { type: Object, required: true },
    kelly: { type: Object, required: true },
    signal: { type: String, default: 'NO_BET' },
    confidence: { type: Number, default: 0 }
  },
  computed: {
    confidencePct() {
      return (this.confidence || 0) * 100
    },
    signalClass() {
      if (!this.signal || this.signal === 'NO_BET') return 'no-bet'
      if (this.signal.includes('HOME')) return 'home-bet'
      return 'away-bet'
    }
  },
  methods: {
    edgeStr(edge) {
      const pct = (edge || 0) * 100
      return pct >= 0 ? `+${pct.toFixed(0)}%` : `${pct.toFixed(0)}%`
    },
    edgeClass(edge) {
      if ((edge || 0) > 0.05) return 'positive'
      if ((edge || 0) < -0.05) return 'negative'
      return 'neutral'
    }
  },
  filters: {
    pct(val) {
      return ((val || 0) * 100).toFixed(0)
    }
  }
}
</script>

<style scoped>
.prediction-card {
  background: #1a1a2e;
  border-radius: 12px;
  padding: 16px;
  border: 1px solid #2a2a4e;
  transition: border-color 0.2s;
}
.prediction-card.home-bet { border-color: #4ade80; }
.prediction-card.away-bet { border-color: #f97316; }
.prediction-card.no-bet { border-color: #4a4a6e; }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.teams { font-size: 18px; font-weight: 700; }
.home-team { color: #fff; }
.vs { color: #888; margin: 0 8px; font-size: 14px; }
.away-team { color: #ccc; }
.signal-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 20px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.home-bet .signal-badge { background: #4ade80; color: #000; }
.away-bet .signal-badge { background: #f97316; color: #000; }
.no-bet .signal-badge { background: #4a4a6e; color: #aaa; }

.confidence-bar {
  height: 3px;
  background: #2a2a4e;
  border-radius: 2px;
  margin-bottom: 14px;
  overflow: hidden;
}
.confidence-fill {
  height: 100%;
  background: linear-gradient(90deg, #4ade80, #60a5fa);
  border-radius: 2px;
  transition: width 0.5s;
}

.bet-types { display: flex; flex-direction: column; gap: 10px; }
.bet-type {
  padding: 10px;
  border-radius: 8px;
  background: #12122a;
  border: 1px solid transparent;
}
.bet-type.highlighted { border-color: #4ade80; background: #0f1f15; }

.bet-label { font-size: 12px; color: #888; display: block; margin-bottom: 4px; }
.prob-row, .kelly-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}
.team-label { color: #aaa; flex: 1; }
.prob-value { color: #fff; font-weight: 600; font-size: 16px; }
.edge { font-size: 12px; font-weight: 600; }
.edge.positive { color: #4ade80; }
.edge.negative { color: #f87171; }
.edge.neutral { color: #888; }
.kelly-label { color: #666; font-size: 12px; }
.kelly-value { font-size: 12px; color: #888; }
.kelly-value.bet { color: #fbbf24; font-weight: 600; }

.baseline {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #2a2a4e;
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}
.baseline-label { color: #666; }
.baseline-value { color: #888; }
</style>
