"""
NBA Data Loader
Loads NBA stats from Kaggle CSVs and serves as the data layer for MiroBet.
Handles 3 seasons: 2022-23, 2023-24, 2024-25
"""
import os
import json
import sqlite3
from typing import Dict, Any, List, Optional
import pandas as pd

class NBADataLoader:
    """NBA data loader from local CSV/ SQLite storage"""

    SEASONS = ['2022-23', '2023-24', '2024-25']

    def __init__(self, data_dir: str = None):
        if data_dir:
            self.data_dir = data_dir
        else:
            # Try to get from MiroBetConfig, fall back to relative path
            try:
                from .mirobet_config import MiroBetConfig
                self.data_dir = MiroBetConfig.NBA_STATS_DIR
            except Exception:
                # Fallback: project root /data/nba_stats
                self.data_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    'data', 'nba_stats'
                )
        os.makedirs(self.data_dir, exist_ok=True)
        self._db_path = os.path.join(self.data_dir, 'nba_stats.db')
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with schema"""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        # Player stats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                team_id TEXT NOT NULL,
                season TEXT NOT NULL,
                games_played INTEGER DEFAULT 0,
                points REAL DEFAULT 0,
                rebounds REAL DEFAULT 0,
                assists REAL DEFAULT 0,
                efg_pct REAL DEFAULT 0,
                usage_rate REAL DEFAULT 0,
                minutes REAL DEFAULT 0,
                steals REAL DEFAULT 0,
                blocks REAL DEFAULT 0,
                turnovers REAL DEFAULT 0,
                UNIQUE(player_name, team_id, season)
            )
        """)

        # Team stats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id TEXT NOT NULL,
                season TEXT NOT NULL,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                home_wins INTEGER DEFAULT 0,
                home_losses INTEGER DEFAULT 0,
                away_wins INTEGER DEFAULT 0,
                away_losses INTEGER DEFAULT 0,
                pace REAL DEFAULT 0,
                defensive_rating REAL DEFAULT 0,
                offensive_rating REAL DEFAULT 0,
                net_rating REAL DEFAULT 0,
                streak TEXT DEFAULT '',
                last_10_wins INTEGER DEFAULT 0,
                last_10_losses INTEGER DEFAULT 0,
                UNIQUE(team_id, season)
            )
        """)

        # Games table (for backtest)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT UNIQUE NOT NULL,
                season TEXT NOT NULL,
                game_date TEXT NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                home_score INTEGER DEFAULT 0,
                away_score INTEGER DEFAULT 0,
                spread REAL DEFAULT 0,
                over_under REAL DEFAULT 0,
                home_ml_odds REAL DEFAULT 0,
                away_ml_odds REAL DEFAULT 0,
                completed INTEGER DEFAULT 0
            )
        """)

        # Matchup history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matchups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_a TEXT NOT NULL,
                team_b TEXT NOT NULL,
                season TEXT NOT NULL,
                team_a_wins INTEGER DEFAULT 0,
                team_b_wins INTEGER DEFAULT 0,
                avg_margin REAL DEFAULT 0,
                UNIQUE(team_a, team_b, season)
            )
        """)

        conn.commit()
        conn.close()

    # ─────────────────────────────────────────────
    # Player stats
    # ─────────────────────────────────────────────

    def get_player_vector(self, player_name: str, season: str) -> Dict[str, float]:
        """Return stat vector for a player: pts, reb, ast, eFG%, usage_rate"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM player_stats
            WHERE player_name = ? AND season = ?
            LIMIT 1
        """, (player_name, season))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'pts': row['points'],
                'reb': row['rebounds'],
                'ast': row['assists'],
                'efg_pct': row['efg_pct'],
                'usage_rate': row['usage_rate'],
                'minutes': row['minutes'],
                'steals': row['steals'],
                'blocks': row['blocks'],
                'turnovers': row['turnovers']
            }

        # Return default if not found
        return {
            'pts': 0.0, 'reb': 0.0, 'ast': 0.0,
            'efg_pct': 0.0, 'usage_rate': 0.0,
            'minutes': 0.0, 'steals': 0.0,
            'blocks': 0.0, 'turnovers': 0.0
        }

    def get_team_players(self, team_id: str, season: str, limit: int = 10) -> List[Dict]:
        """Get top N players for a team by points"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM player_stats
            WHERE team_id = ? AND season = ?
            ORDER BY points DESC
            LIMIT ?
        """, (team_id, season, limit))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    # ─────────────────────────────────────────────
    # Team stats
    # ─────────────────────────────────────────────

    def get_team_form_tensor(self, team_id: str, season: str) -> Dict[str, Any]:
        """Return team form: last 10 games, home/away splits, pace, defensive rating"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM team_stats
            WHERE team_id = ? AND season = ?
            LIMIT 1
        """, (team_id, season))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'last_10_wins': row['last_10_wins'],
                'last_10_losses': row['last_10_losses'],
                'home_record': f"{row['home_wins']}-{row['home_losses']}",
                'away_record': f"{row['away_wins']}-{row['away_losses']}",
                'pace': row['pace'],
                'defensive_rating': row['defensive_rating'],
                'offensive_rating': row['offensive_rating'],
                'net_rating': row['net_rating'],
                'streak': row['streak'],
                'total_wins': row['wins'],
                'total_losses': row['losses']
            }

        return {
            'last_10_wins': 0, 'last_10_losses': 0,
            'home_record': '0-0', 'away_record': '0-0',
            'pace': 0.0, 'defensive_rating': 0.0,
            'offensive_rating': 0.0, 'net_rating': 0.0,
            'streak': '', 'total_wins': 0, 'total_losses': 0
        }

    def get_team_stats(self, team_id: str, season: str) -> Dict[str, Any]:
        """Alias for get_team_form_tensor"""
        return self.get_team_form_tensor(team_id, season)

    def get_team_form(self, team_id: str, season: str) -> Dict[str, Any]:
        """Alias for get_team_form_tensor"""
        return self.get_team_form_tensor(team_id, season)

    # ─────────────────────────────────────────────
    # Matchup history
    # ─────────────────────────────────────────────

    def get_matchup_history(self, team_a: str, team_b: str, season: str = None) -> Dict[str, Any]:
        """Return H2H records, positional mismatches"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if season:
            cursor.execute("""
                SELECT * FROM matchups
                WHERE ((team_a = ? AND team_b = ?) OR (team_a = ? AND team_b = ?))
                AND season = ?
                LIMIT 1
            """, (team_a, team_b, team_b, team_a, season))
        else:
            # Get most recent season data
            cursor.execute("""
                SELECT * FROM matchups
                WHERE (team_a = ? AND team_b = ?) OR (team_a = ? AND team_b = ?)
                ORDER BY season DESC
                LIMIT 1
            """, (team_a, team_b, team_b, team_a))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'team_a_wins': row['team_a_wins'],
                'team_b_wins': row['team_b_wins'],
                'avg_margin': row['avg_margin']
            }

        return {'team_a_wins': 0, 'team_b_wins': 0, 'avg_margin': 0.0}

    # ─────────────────────────────────────────────
    # Game data (for backtest)
    # ─────────────────────────────────────────────

    def get_season_games(self, season: str) -> List[Dict[str, Any]]:
        """Get all games for a season"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM games
            WHERE season = ? AND completed = 1
            ORDER BY game_date
        """, (season,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def build_game_context(self, game: Dict, season: str) -> Dict[str, Any]:
        """Build complete game context for agent prompts"""
        home_team = game['home_team']
        away_team = game['away_team']

        return {
            'home_team': home_team,
            'away_team': away_team,
            'season': season,
            'game_date': game.get('game_date', ''),
            'home_stats': self.get_team_stats(home_team, season),
            'away_stats': self.get_team_stats(away_team, season),
            'home_form': self.get_team_form(home_team, season),
            'away_form': self.get_team_form(away_team, season),
            'h2h': self.get_matchup_history(home_team, away_team, season),
            'home_players': self.get_team_players(home_team, season, 10),
            'away_players': self.get_team_players(away_team, season, 10)
        }

    # ─────────────────────────────────────────────
    # Data import (from CSV)
    # ─────────────────────────────────────────────

    def import_player_stats_csv(self, csv_path: str):
        """Import player stats from Kaggle CSV"""
        df = pd.read_csv(csv_path)

        # Normalize column names
        column_map = {
            'PLAYER_NAME': 'player_name',
            'TEAM_ID': 'team_id',
            'SEASON': 'season',
            'GP': 'games_played',
            'PTS': 'points',
            'REB': 'rebounds',
            'AST': 'assists',
            'EFG_PCT': 'efg_pct',
            'USAGE_PCT': 'usage_rate',
            'MIN': 'minutes',
            'STL': 'steals',
            'BLK': 'blocks',
            'TOV': 'turnovers',
        }

        df = df.rename(columns=column_map)
        required = ['player_name', 'team_id', 'season']
        df = df.dropna(subset=required)

        conn = sqlite3.connect(self._db_path)
        df.to_sql('player_stats', conn, if_exists='append', index=False)
        conn.commit()
        conn.close()

    def import_team_stats_csv(self, csv_path: str):
        """Import team stats from Kaggle CSV"""
        df = pd.read_csv(csv_path)

        column_map = {
            'TEAM_ID': 'team_id',
            'SEASON': 'season',
            'W': 'wins',
            'L': 'losses',
            'HOME_W': 'home_wins',
            'HOME_L': 'home_losses',
            'AWAY_W': 'away_wins',
            'AWAY_L': 'away_losses',
            'PACE': 'pace',
            'DEF_RTG': 'defensive_rating',
            'OFF_RTG': 'offensive_rating',
            'NET_RTG': 'net_rating',
            'STRK': 'streak',
            'L10_W': 'last_10_wins',
            'L10_L': 'last_10_losses',
        }

        df = df.rename(columns=column_map)
        required = ['team_id', 'season']
        df = df.dropna(subset=required)

        conn = sqlite3.connect(self._db_path)
        df.to_sql('team_stats', conn, if_exists='append', index=False)
        conn.commit()
        conn.close()

    def import_games_csv(self, csv_path: str):
        """Import game results from Kaggle CSV"""
        df = pd.read_csv(csv_path)

        column_map = {
            'GAME_ID': 'game_id',
            'SEASON': 'season',
            'GAME_DATE': 'game_date',
            'HOME_TEAM': 'home_team',
            'AWAY_TEAM': 'away_team',
            'HOME_PTS': 'home_score',
            'AWAY_PTS': 'away_score',
            'SPREAD': 'spread',
            'OU': 'over_under',
            'HOME_ML': 'home_ml_odds',
            'AWAY_ML': 'away_ml_odds',
        }

        df = df.rename(columns=column_map)
        required = ['game_id', 'season', 'home_team', 'away_team']
        df = df.dropna(subset=required)
        df['completed'] = 1

        conn = sqlite3.connect(self._db_path)
        df.to_sql('games', conn, if_exists='append', index=False)
        conn.commit()
        conn.close()
