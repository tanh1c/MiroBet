"""
NBA Data Loader
Loads stats from Kaggle CSVs and serves as the data layer for MiroBet.
"""
import os
import sqlite3
import pandas as pd
from typing import Dict, List


class NBADataLoader:

    SEASONS = ["2022-23", "2023-24", "2024-25"]

    def __init__(self, data_dir=None):
        if data_dir:
            self.data_dir = data_dir
        else:
            _p = os.path.dirname(os.path.abspath(__file__))
            _p = os.path.dirname(_p)
            _p = os.path.dirname(_p)
            self.data_dir = os.path.join(_p, "kaggle_data")
        os.makedirs(self.data_dir, exist_ok=True)
        self._db_path = os.path.join(self.data_dir, "nba_stats.db")
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS player_stats (
            player_name TEXT NOT NULL, team_id TEXT NOT NULL, season TEXT NOT NULL,
            games_played INTEGER DEFAULT 0, points REAL DEFAULT 0,
            rebounds REAL DEFAULT 0, assists REAL DEFAULT 0,
            efg_pct REAL DEFAULT 0, usage_rate REAL DEFAULT 0,
            minutes REAL DEFAULT 0, steals REAL DEFAULT 0,
            blocks REAL DEFAULT 0, turnovers REAL DEFAULT 0,
            PRIMARY KEY (player_name, team_id, season))""")
        c.execute("""CREATE TABLE IF NOT EXISTS team_stats (
            team_id TEXT NOT NULL, season TEXT NOT NULL,
            wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0,
            home_wins INTEGER DEFAULT 0, home_losses INTEGER DEFAULT 0,
            away_wins INTEGER DEFAULT 0, away_losses INTEGER DEFAULT 0,
            pace REAL DEFAULT 0, defensive_rating REAL DEFAULT 0,
            offensive_rating REAL DEFAULT 0, net_rating REAL DEFAULT 0,
            streak TEXT DEFAULT "",
            last_10_wins INTEGER DEFAULT 0, last_10_losses INTEGER DEFAULT 0,
            UNIQUE(team_id, season))""")
        c.execute("""CREATE TABLE IF NOT EXISTS games (
            game_id TEXT UNIQUE NOT NULL, season TEXT NOT NULL,
            game_date TEXT NOT NULL, home_team TEXT NOT NULL, away_team TEXT NOT NULL,
            home_score INTEGER DEFAULT 0, away_score INTEGER DEFAULT 0,
            spread REAL DEFAULT 0, over_under REAL DEFAULT 0,
            home_ml_odds REAL DEFAULT 0, away_ml_odds REAL DEFAULT 0,
            completed INTEGER DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS matchups (
            team_a TEXT NOT NULL, team_b TEXT NOT NULL, season TEXT NOT NULL,
            team_a_wins INTEGER DEFAULT 0, team_b_wins INTEGER DEFAULT 0,
            avg_margin REAL DEFAULT 0,
            UNIQUE(team_a, team_b, season))""")
        conn.commit()
        conn.close()

    # ─────────────────────────────────────────────────────────────────────
    # Getters
    # ─────────────────────────────────────────────────────────────────────

    def get_player_vector(self, player_name: str, season: str) -> Dict:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            "SELECT * FROM player_stats WHERE player_name=? AND season=? LIMIT 1",
            (player_name, season))
        row = c.fetchone()
        conn.close()
        if row:
            return dict(row)
        return {
            "points": 0, "rebounds": 0, "assists": 0,
            "efg_pct": 0, "usage_rate": 0, "minutes": 0,
            "steals": 0, "blocks": 0, "turnovers": 0,
            "games_played": 0}

    def get_team_players(self, team_id: str, season: str, limit: int = 10) -> List[Dict]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            "SELECT * FROM player_stats WHERE team_id=? AND season=? "
            "ORDER BY points DESC LIMIT ?",
            (team_id, season, limit))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_team_form_tensor(self, team_id: str, season: str) -> Dict:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            "SELECT * FROM team_stats WHERE team_id=? AND season=? LIMIT 1",
            (team_id, season))
        row = c.fetchone()
        conn.close()
        if row:
            d = dict(row)
            d["home_record"] = f"{d.get('home_wins', 0)}-{d.get('home_losses', 0)}"
            d["away_record"] = f"{d.get('away_wins', 0)}-{d.get('away_losses', 0)}"
            d["total_wins"] = d.get("wins", 0)
            d["total_losses"] = d.get("losses", 0)
            return d
        return {
            "last_10_wins": 0, "last_10_losses": 0,
            "home_record": "0-0", "away_record": "0-0",
            "pace": 0, "defensive_rating": 0, "offensive_rating": 0,
            "net_rating": 0, "streak": "",
            "wins": 0, "losses": 0}

    def get_team_stats(self, team_id: str, season: str) -> Dict:
        return self.get_team_form_tensor(team_id, season)

    def get_team_form(self, team_id: str, season: str) -> Dict:
        return self.get_team_form_tensor(team_id, season)

    def get_matchup_history(self, team_a: str, team_b: str, season=None) -> Dict:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        if season:
            c.execute(
                "SELECT * FROM matchups WHERE "
                "(team_a=? AND team_b=?) OR (team_a=? AND team_b=?) "
                "AND season=? LIMIT 1",
                (team_a, team_b, team_b, team_a, season))
        else:
            c.execute(
                "SELECT * FROM matchups WHERE "
                "(team_a=? AND team_b=?) OR (team_a=? AND team_b=?) "
                "ORDER BY season DESC LIMIT 1",
                (team_a, team_b, team_b, team_a))
        row = c.fetchone()
        conn.close()
        if row:
            return dict(row)
        return {"team_a_wins": 0, "team_b_wins": 0, "avg_margin": 0}

    def get_season_games(self, season: str) -> List[Dict]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            "SELECT * FROM games WHERE season=? AND completed=1 ORDER BY game_date",
            (season,))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def build_game_context(self, game: Dict, season: str) -> Dict:
        home = game["home_team"]
        away = game["away_team"]
        return {
            "home_team": home,
            "away_team": away,
            "season": season,
            "game_date": game.get("game_date", ""),
            "home_stats": self.get_team_stats(home, season),
            "away_stats": self.get_team_stats(away, season),
            "home_form": self.get_team_form(home, season),
            "away_form": self.get_team_form(away, season),
            "h2h": self.get_matchup_history(home, away, season),
            "home_players": self.get_team_players(home, season, 10),
            "away_players": self.get_team_players(away, season, 10),
        }

    # ─────────────────────────────────────────────────────────────────────
    # Kaggle CSV import
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _infer_season(dt_str: str) -> str:
        """'2024-03-15T00:00:00' -> '2023-24'"""
        try:
            month = int(str(dt_str)[5:7])
            year = int(str(dt_str)[:4])
            yr = year if month >= 10 else year - 1
            return f"{yr}-{str(yr + 1)[-2:].zfill(2)}"
        except Exception:
            return "2024-25"

    def _build_team_id_map(self, team_stats_csv: str) -> dict:
        """Build playerteamName -> teamId mapping from TeamStatistics.csv (filter to NBA only)."""
        tdf = pd.read_csv(team_stats_csv, usecols=["teamId", "teamName", "teamCity"],
                          low_memory=False)
        tdf["teamId"] = tdf["teamId"].astype(str).str.strip()
        tdf["teamName"] = tdf["teamName"].astype(str).str.strip()
        tdf["teamCity"] = tdf["teamCity"].astype(str).str.strip()
        # Only keep numeric NBA team IDs (real franchises)
        nba = tdf[tdf["teamId"].str.startswith("16106", na=False)].copy()
        # Pick the most common teamId per (teamCity, teamName) — handles rebranding
        best = nba.groupby(["teamCity", "teamName"])["teamId"].agg(
            lambda x: x.value_counts().index[0]).reset_index()
        best["full_name"] = best["teamCity"] + " " + best["teamName"]
        return dict(zip(best["teamName"].str.strip(), best["teamId"])), \
            set(best["teamId"].tolist())

    def import_player_stats_csv(self, csv_path: str):
        """Import PlayerStatistics.csv (game-by-game box scores). Aggregates to season averages per player."""
        df = pd.read_csv(csv_path, low_memory=False)
        # Full name
        df["player_name"] = (
            df["firstName"].fillna("").astype(str) + " " +
            df["lastName"].fillna("").astype(str)).str.strip()
        df["season"] = df["gameDateTimeEst"].apply(self._infer_season)
        # Map playerteamName -> numeric team_id using TeamStatistics.csv
        team_stats_csv = csv_path.replace("PlayerStatistics", "TeamStatistics")
        if os.path.exists(team_stats_csv):
            name_map, valid_ids = self._build_team_id_map(team_stats_csv)
        else:
            name_map, valid_ids = {}, set()
        df["team_id"] = df["playerteamName"].astype(str).str.strip().map(name_map)
        # Drop rows where team_id could not be resolved to a valid NBA team
        before = len(df)
        df = df[df["team_id"].isin(valid_ids)].copy()
        after = len(df)
        if after < before:
            print(f"  Dropped {before - after} non-NBA rows")
        df["team_id"] = df["team_id"].astype(str)
        # eFG%
        fga = pd.to_numeric(df["fieldGoalsAttempted"], errors="coerce").fillna(0)
        fga = fga.replace(0, float("nan"))
        df["efg_pct"] = (
            pd.to_numeric(df["fieldGoalsMade"], errors="coerce").fillna(0) +
            0.5 * pd.to_numeric(df["threePointersMade"], errors="coerce").fillna(0)
        ) / fga.fillna(1).replace(0, 1)
        # Usage rate
        mins = pd.to_numeric(df["numMinutes"], errors="coerce").fillna(1).replace(0, 1)
        df["usage_rate"] = pd.to_numeric(df["fieldGoalsAttempted"], errors="coerce").fillna(0) / mins
        df["games_played"] = 1  # each row = one game appearance
        # Coerce all stat columns to numeric
        stat_cols = ["points", "reboundsTotal", "assists", "efg_pct",
                     "usage_rate", "numMinutes", "steals", "blocks", "turnovers"]
        for c in stat_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        # Season-average aggregation per (player, team, season)
        agg = df.groupby(["player_name", "team_id", "season"]).agg({
            "games_played": "sum",
            "points": "mean",
            "reboundsTotal": "mean",
            "assists": "mean",
            "efg_pct": "mean",
            "usage_rate": "mean",
            "numMinutes": "mean",
            "steals": "mean",
            "blocks": "mean",
            "turnovers": "mean",
        }).reset_index()
        agg = agg.rename(columns={
            "reboundsTotal": "rebounds",
            "numMinutes": "minutes",
        })
        conn = sqlite3.connect(self._db_path)
        agg.to_sql("player_stats", conn, if_exists="append", index=False)
        conn.commit()
        conn.close()

    def import_team_stats_csv(self, csv_path: str):
        """Import TeamStatistics.csv game-level, then aggregate to season totals."""
        df = pd.read_csv(csv_path, low_memory=False)
        df["team_id"] = df["teamId"].astype(str)
        df["season"] = df["gameDateTimeEst"].apply(self._infer_season)
        df["win_flag"] = (df["win"] == 1).astype(int)
        # Home/away splits from 'home' flag
        df["home_win"] = ((df["win"] == 1) & (df["home"] == 1)).astype(int)
        df["home_loss"] = ((df["win"] == 0) & (df["home"] == 1)).astype(int)
        df["away_win"] = ((df["win"] == 1) & (df["home"] == 0)).astype(int)
        df["away_loss"] = ((df["win"] == 0) & (df["home"] == 0)).astype(int)
        agg = df.groupby(["team_id", "season"]).agg({
            "win_flag": "sum",     # total wins from game-level data
            "home_win": "sum",
            "home_loss": "sum",
            "away_win": "sum",
            "away_loss": "sum",
        }).reset_index()
        agg = agg.rename(columns={"win_flag": "wins"})
        agg["home_wins"] = agg["home_win"].astype(int)
        agg["home_losses"] = agg["home_loss"].astype(int)
        agg["away_wins"] = agg["away_win"].astype(int)
        agg["away_losses"] = agg["away_loss"].astype(int)
        agg["wins"] = agg["wins"].astype(int)
        # losses = home_losses + away_losses (direct count, not derived)
        agg["losses"] = agg["home_losses"] + agg["away_losses"]
        keep = ["team_id", "season", "wins", "losses",
                "home_wins", "home_losses", "away_wins", "away_losses"]
        agg = agg[keep]
        conn = sqlite3.connect(self._db_path)
        agg.to_sql("team_stats", conn, if_exists="append", index=False)
        conn.commit()
        conn.close()

    def import_team_advanced_csv(self, csv_path: str):
        """Import TeamStatisticsAdvanced.csv to add pace/ratings to existing team_stats."""
        df = pd.read_csv(csv_path)
        if df.empty:
            return
        df["team_id"] = df["teamId"].astype(str)
        df["season"] = df["gameDateTimeEst"].apply(self._infer_season)
        agg = df.groupby(["team_id", "season"]).agg({
            "pace": "mean",
            "offRating": "mean",
            "defRating": "mean",
            "netRating": "mean",
        }).reset_index()
        conn = sqlite3.connect(self._db_path)
        for _, row in agg.iterrows():
            c = conn.cursor()
            c.execute(
                "UPDATE team_stats SET "
                "pace=?, offensive_rating=?, defensive_rating=?, net_rating=? "
                "WHERE team_id=? AND season=?",
                (row["pace"], row["offRating"], row["defRating"],
                 row["netRating"], row["team_id"], row["season"]))
        conn.commit()
        conn.close()

    def import_games_csv(self, csv_path: str):
        """Import Games.csv."""
        df = pd.read_csv(csv_path)
        df = df.rename(columns={
            "gameId": "game_id",
            "gameDateTimeEst": "game_date",
            "hometeamId": "home_team",
            "awayteamId": "away_team",
            "homeScore": "home_score",
            "awayScore": "away_score",
        })
        df["home_team"] = df["home_team"].astype(str)
        df["away_team"] = df["away_team"].astype(str)
        df["game_id"] = df["game_id"].astype(str)
        df["season"] = df["game_date"].apply(self._infer_season)
        df["completed"] = 1
        keep = ["game_id", "season", "game_date", "home_team", "away_team",
                "home_score", "away_score", "completed"]
        df = df[[c for c in keep if c in df.columns]]
        conn = sqlite3.connect(self._db_path)
        df.to_sql("games", conn, if_exists="append", index=False)
        conn.commit()
        conn.close()

    def compute_matchups(self):
        """Compute H2H from games and store in matchups table."""
        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        c.execute("DELETE FROM matchups")
        c.execute("""INSERT INTO matchups
            (team_a, team_b, season, team_a_wins, team_b_wins, avg_margin)
            SELECT
                home_team AS team_a, away_team AS team_b, season,
                SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) AS team_a_wins,
                SUM(CASE WHEN away_score > home_score THEN 1 ELSE 0 END) AS team_b_wins,
                AVG(CAST(home_score - away_score AS REAL)) AS avg_margin
            FROM games
            WHERE completed=1
            GROUP BY home_team, away_team, season""")
        conn.commit()
        conn.close()

    def import_all(self, kaggle_dir=None):
        """Import all Kaggle CSVs from directory."""
        d = kaggle_dir or self.data_dir
        import os
        files = {f: os.path.join(d, f) for f in os.listdir(d) if f.endswith(".csv")}
        if "PlayerStatistics.csv" in files:
            print(f"  Importing player stats: {files['PlayerStatistics.csv']}")
            self.import_player_stats_csv(files["PlayerStatistics.csv"])
        if "TeamStatistics.csv" in files:
            print(f"  Importing team stats: {files['TeamStatistics.csv']}")
            self.import_team_stats_csv(files["TeamStatistics.csv"])
        if "TeamStatisticsAdvanced.csv" in files:
            print(f"  Importing team advanced: {files['TeamStatisticsAdvanced.csv']}")
            self.import_team_advanced_csv(files["TeamStatisticsAdvanced.csv"])
        if "Games.csv" in files:
            print(f"  Importing games: {files['Games.csv']}")
            self.import_games_csv(files["Games.csv"])
            print("  Computing matchups...")
            self.compute_matchups()
        print("Done!")
