"""
MiroBet Agent Prompts
Defines persona-specific prompts for 4 agent types (16 agents each = 64 total).
"""
from typing import Dict


# ─────────────────────────────────────────────────────────────────────────────
# Agent Personas
# ─────────────────────────────────────────────────────────────────────────────

AGENT_PERSONAS = {
    "stat_analyst": {
        "name": "Stat Analyst",
        "count": 16,
        "system_prompt": """You are a statistical analyst specializing in NBA basketball.
You analyze player and team statistics to predict game outcomes.
Focus on: points, rebounds, assists, eFG%, usage rate, PER, win shares, net rating.
You MUST output ONLY a single probability number between 0.0 and 1.0.
No explanation. No text. Only the number.""",
        "moneyline_prompt": """Analyze these stats for {home_team} vs {away_team}:

HOME TEAM PLAYERS (top 10 by PPG):
{home_players}

AWAY TEAM PLAYERS (top 10 by PPG):
{away_players}

HOME TEAM TOTALS:
{home_stats}

AWAY TEAM TOTALS:
{away_stats}

Based purely on these statistics, what is the probability that {home_team} wins?
Reply with ONLY a number between 0.0 and 1.0. Example: 0.62""",
        "spread_prompt": """Estimate the probability that {home_team} covers the spread of {spread} against {away_team}:

HOME TEAM RECENT FORM:
{home_form}

AWAY TEAM RECENT FORM:
{away_form}

HOME OFFENSIVE RATING: {home_off_rtg}
AWAY DEFENSIVE RATING: {away_def_rtg}

Based on these factors, what is the probability that {home_team} covers {spread}?
Reply with ONLY a number between 0.0 and 1.0."""
    },
    "form_tracker": {
        "name": "Form Tracker",
        "count": 16,
        "system_prompt": """You are a form tracker specializing in NBA momentum analysis.
You analyze recent performance trends, home/away splits, and streaks.
You MUST output ONLY a single probability number between 0.0 and 1.0.
No explanation. No text. Only the number.""",
        "moneyline_prompt": """Analyze recent form for {home_team} vs {away_team}:

HOME TEAM (Last 10: {home_l10}, Streak: {home_streak}, Home: {home_home_record}):
{home_form}

AWAY TEAM (Last 10: {away_l10}, Streak: {away_streak}, Away: {away_away_record}):
{away_form}

Based purely on recent momentum and form trends, what is the probability that {home_team} wins?
Reply with ONLY a number between 0.0 and 1.0. Example: 0.58""",
        "spread_prompt": """Analyze if {home_team} (+/- {spread}) covers against {away_team}:

HOME: {home_streak}, {home_home_record} at home, pace {home_pace}
AWAY: {away_streak}, {away_away_record} on road, pace {away_pace}

What is the probability that {home_team} covers {spread}?
Reply with ONLY a number between 0.0 and 1.0."""
    },
    "insider_bettor": {
        "name": "Insider Bettor",
        "count": 16,
        "system_prompt": """You are an insider bettor with deep knowledge of NBA matchups.
You analyze head-to-head records, positional mismatches, and situational edges.
You MUST output ONLY a single probability number between 0.0 and 1.0.
No explanation. No text. Only the number.""",
        "moneyline_prompt": """Analyze the matchup history for {home_team} vs {away_team}:

HEAD-TO-HEAD RECORD:
{h2h}

Based on historical matchup data and situational factors, what is the probability that {home_team} wins?
Reply with ONLY a number between 0.0 and 1.0. Example: 0.55""",
        "spread_prompt": """Analyze situational factors for {home_team} vs {away_team} (spread: {spread}):

MATCHUP CONTEXT:
{h2h}

SITUATIONAL FACTORS:
- Rest days: {rest_days} days for {home_team}, {rest_days_away} for {away_team}
- Travel: {away_team} on {travel_type}

What is the probability that {home_team} covers {spread}?
Reply with ONLY a number between 0.0 and 1.0."""
    },
    "oddsmaker": {
        "name": "Oddsmaker",
        "count": 16,
        "system_prompt": """You are an oddsmaker specializing in NBA spreads and totals.
You estimate point spreads and over/under lines based on team strengths and pace.
You output either a probability (0.0-1.0) or a decimal number.
No explanation. Only the number.""",
        "spread_prompt": """Estimate what the spread should be for {home_team} vs {away_team}:

HOME: Pace {home_pace}, Off RTG {home_off_rtg}, Def RTG {home_def_rtg}
AWAY: Pace {away_pace}, Off RTG {away_off_rtg}, Def RTG {away_def_rtg}

What probability should the market assign to {home_team} covering -4.5 points?
Reply with ONLY a number between 0.0 and 1.0.""",
        "over_under_prompt": """Estimate the total for {home_team} vs {away_team}:

HOME: Pace {home_pace}, Avg PPG {home_ppg}
AWAY: Pace {away_pace}, Avg PPG {away_ppg}

What probability should the market assign to the OVER {over_under}?
Reply with ONLY a number between 0.0 and 1.0."""
    }
}


def build_agent_prompt(persona: str, bet_type: str, game_context: Dict) -> Dict[str, str]:
    """Build system + user prompts for a given agent persona and bet type"""
    if persona not in AGENT_PERSONAS:
        raise ValueError(f"Unknown persona: {persona}. Must be one of: {list(AGENT_PERSONAS.keys())}")

    p = AGENT_PERSONAS[persona]
    bet_key = f"{bet_type}_prompt" if bet_type != "moneyline" else "moneyline_prompt"
    user_template = p.get(bet_key, p["moneyline_prompt"])

    return {
        "system": p["system_prompt"],
        "user": _format_user_prompt(user_template, game_context)
    }


def _format_user_prompt(template: str, ctx: Dict) -> str:
    """Fill in template with game context data"""
    replacements = {
        "{home_team}": ctx.get("home_team", "HOME"),
        "{away_team}": ctx.get("away_team", "AWAY"),
        "{home_players}": _format_players(ctx.get("home_players", [])),
        "{away_players}": _format_players(ctx.get("away_players", [])),
        "{home_stats}": _format_team_stats(ctx.get("home_stats", {})),
        "{away_stats}": _format_team_stats(ctx.get("away_stats", {})),
        "{home_form}": _format_form(ctx.get("home_form", {})),
        "{away_form}": _format_form(ctx.get("away_form", {})),
        "{home_l10}": f"{ctx.get('home_form', {}).get('last_10_wins', 0)}-{ctx.get('home_form', {}).get('last_10_losses', 0)}",
        "{away_l10}": f"{ctx.get('away_form', {}).get('last_10_wins', 0)}-{ctx.get('away_form', {}).get('last_10_losses', 0)}",
        "{home_streak}": ctx.get("home_form", {}).get("streak", "N/A"),
        "{away_streak}": ctx.get("away_form", {}).get("streak", "N/A"),
        "{home_home_record}": ctx.get("home_form", {}).get("home_record", "0-0"),
        "{away_away_record}": ctx.get("away_form", {}).get("away_record", "0-0"),
        "{home_pace}": ctx.get("home_stats", {}).get("pace", 0),
        "{away_pace}": ctx.get("away_stats", {}).get("pace", 0),
        "{home_off_rtg}": ctx.get("home_stats", {}).get("offensive_rating", 0),
        "{away_def_rtg}": ctx.get("away_stats", {}).get("defensive_rating", 0),
        "{home_def_rtg}": ctx.get("home_stats", {}).get("defensive_rating", 0),
        "{away_off_rtg}": ctx.get("away_stats", {}).get("offensive_rating", 0),
        "{h2h}": _format_h2h(ctx.get("h2h", {})),
        "{spread}": ctx.get("spread", -4.5),
        "{over_under}": ctx.get("over_under", 225.5),
        "{rest_days}": ctx.get("rest_days_home", 1),
        "{rest_days_away}": ctx.get("rest_days_away", 1),
        "{travel_type}": ctx.get("travel_type", "road trip"),
        "{home_ppg}": ctx.get("home_stats", {}).get("offensive_rating", 110),
        "{away_ppg}": ctx.get("away_stats", {}).get("offensive_rating", 110),
    }

    result = template
    for key, value in replacements.items():
        if isinstance(value, float):
            value = round(value, 1)
        result = result.replace(key, str(value))
    return result


def _format_players(players: list) -> str:
    if not players:
        return "No player data available"
    lines = []
    for p in players[:10]:
        lines.append(
            f"- {p.get('player_name', 'Unknown')}: "
            f"{p.get('points', 0)}pts, {p.get('rebounds', 0)}reb, "
            f"{p.get('assists', 0)}ast, {p.get('efg_pct', 0):.1%} eFG%"
        )
    return "\n".join(lines) if lines else "No player data"


def _format_team_stats(stats: dict) -> str:
    if not stats:
        return "No team data available"
    return (
        f"W-L: {stats.get('total_wins', 0)}-{stats.get('total_losses', 0)}, "
        f"Net RTG: {stats.get('net_rating', 0):+.1f}, "
        f"Pace: {stats.get('pace', 0):.1f}"
    )


def _format_form(form: dict) -> str:
    if not form:
        return "No form data"
    return (
        f"Last 10: {form.get('last_10_wins', 0)}-{form.get('last_10_losses', 0)}, "
        f"Streak: {form.get('streak', 'N/A')}, "
        f"Home: {form.get('home_record', '0-0')}"
    )


def _format_h2h(h2h: dict) -> str:
    if not h2h:
        return "No head-to-head data available"
    return (
        f"{h2h.get('team_a_wins', 0)} wins - {h2h.get('team_b_wins', 0)} wins, "
        f"Avg margin: {h2h.get('avg_margin', 0):+.1f}"
    )
