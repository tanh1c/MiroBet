"""
Agent Voter - Runs 64 agents in parallel via Groq API
"""
import os
import re
import asyncio
from typing import List, Dict, Any

from .llm_client import LLMClient
from .agent_prompts import AGENT_PERSONAS, build_agent_prompt
from .mirobet_config import MiroBetConfig


class AgentVoter:
    """
    Runs MiroFish consensus voting with 64 agents (4 personas × 16 agents).

    Each agent is an independent LLM call with a sports-specific persona.
    Results are aggregated into a consensus probability.
    """

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.llm = LLMClient(
            api_key=api_key or MiroBetConfig.LLM_API_KEY,
            base_url=base_url or MiroBetConfig.LLM_BASE_URL,
            model=model or MiroBetConfig.LLM_MODEL_NAME
        )
        self.agent_count = MiroBetConfig.AGENT_COUNT
        self.personas = list(AGENT_PERSONAS.keys())
        self.agents_per_persona = MiroBetConfig.AGENTS_PER_PERSONA

    def run_all_personas(self, game_context: Dict, bet_type: str = "moneyline") -> List[float]:
        """
        Run all agents for a given bet type and return list of votes.
        Uses asyncio for parallel LLM calls.
        """
        return asyncio.run(self._run_all_personas_async(game_context, bet_type))

    async def _run_all_personas_async(self, game_context: Dict, bet_type: str) -> List[float]:
        """Async version of run_all_personas"""
        all_tasks = []
        for persona in self.personas:
            task = self._run_persona_async(persona, game_context, bet_type)
            all_tasks.append(task)

        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        all_votes = []
        for result in results:
            if isinstance(result, list):
                all_votes.extend(result)
            elif isinstance(result, Exception):
                # Log error but continue
                pass
        return all_votes

    async def _run_persona_async(self, persona: str, game_context: Dict, bet_type: str) -> List[float]:
        """Run all agents of one persona type in parallel"""
        tasks = []
        for i in range(self.agents_per_persona):
            task = self._call_agent_async(persona, game_context, bet_type, agent_idx=i)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        votes = []
        for result in results:
            if isinstance(result, float) and 0.0 <= result <= 1.0:
                votes.append(result)
        return votes

    async def _call_agent_async(self, persona: str, game_context: Dict, bet_type: str, agent_idx: int) -> float:
        """Call LLM for a single agent"""
        prompts = build_agent_prompt(persona, bet_type, game_context)

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.llm.chat(
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]}
                ],
                temperature=0.7,
                max_tokens=MiroBetConfig.MAX_TOKENS_PER_CALL
            )
        )

        return self._parse_vote(response)

    def _parse_vote(self, response: str) -> float:
        """Parse LLM response to extract probability vote"""
        if not response:
            return 0.5

        # Try to find a number between 0.0 and 1.0
        matches = re.findall(r'0?\.\d+', str(response))
        for match in matches:
            try:
                value = float(match)
                if 0.0 <= value <= 1.0:
                    return round(value, 4)
            except ValueError:
                pass

        # Try percentage format (e.g., "62%" or "62 percent")
        pct_matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', str(response))
        for match in pct_matches:
            try:
                value = float(match) / 100
                if 0.0 <= value <= 1.0:
                    return round(value, 4)
            except ValueError:
                pass

        return 0.5  # Default if parsing fails

    def run_persona_sync(self, persona: str, game_context: Dict, bet_type: str = "moneyline") -> List[float]:
        """Synchronous version — for debugging or single persona testing"""
        votes = []
        for i in range(self.agents_per_persona):
            prompts = build_agent_prompt(persona, bet_type, game_context)
            response = self.llm.chat(
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]}
                ],
                temperature=0.7,
                max_tokens=MiroBetConfig.MAX_TOKENS_PER_CALL
            )
            vote = self._parse_vote(response)
            votes.append(vote)
        return votes

    def get_persona_breakdown(self, game_context: Dict, bet_type: str = "moneyline") -> Dict[str, float]:
        """Run all personas and return breakdown by persona"""
        breakdown = {}
        for persona in self.personas:
            votes = self.run_persona_sync(persona, game_context, bet_type)
            if votes:
                breakdown[persona] = round(sum(votes) / len(votes), 4)
            else:
                breakdown[persona] = 0.5
        return breakdown
