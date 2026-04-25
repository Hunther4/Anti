"""
Process Reward Model (PRM) scorer.
Refactored to use requests instead of openai library.
"""

import asyncio
import collections
import logging
import re
import requests
from typing import Any, Optional

logger = logging.getLogger(__name__)

_BOXED_RE = re.compile(r"\\boxed\{([-+]?\d)\}")
_SCORE_RE = re.compile(r"Score:\s*([-+]?\d)", re.IGNORECASE)

_GREEN = "\033[32m"
_CYAN = "\033[36m"
_RESET = "\033[0m"


def _sanitize_text(text: str) -> str:
    """Replace XML-like tags that may trigger content filters."""
    import re as _re
    text = _re.sub(r"<tool_call>.*?</tool_call>", "[tool_call block]", text, flags=_re.DOTALL)
    text = _re.sub(r"<[a-zA-Z_][^>]{0,80}>", "[tag]", text)
    text = _re.sub(r"</[a-zA-Z_][^>]{0,80}>", "[/tag]", text)
    return text


def _build_prm_judge_prompt(response_text: str, instruction_text: str) -> list[dict]:
    """Construct the judge messages for PRM evaluation."""
    system = (
        "You are a quality reviewer for conversational responses.\n"
        "You will be shown a user instruction and the assistant response to that instruction.\n"
        "Based on instruction alignment and task completion quality, decide whether the response was "
        "helpful (+1), unhelpful (-1), or unclear (0).\n"
        "Do NOT compare against any follow-up turn.\n"
        "Only evaluate whether the response addresses the given instruction.\n"
        "Use +1 when the response clearly follows and substantially completes the instruction.\n"
        "Use -1 when the response is off-task, wrong, or fails to complete core requirements.\n"
        "Use 0 when completion is ambiguous or evidence is insufficient.\n"
        "Think briefly, then end your reply with exactly one of: Score: 1 / Score: -1 / Score: 0"
    )
    clean_instruction = _sanitize_text(instruction_text)
    clean_response = _sanitize_text(response_text)
    user = (
        f"Instruction:\n{clean_instruction}\n\n"
        f"Response:\n{clean_response}\n\n"
        "Was the response helpful for this instruction? "
        "End with Score: 1, Score: -1, or Score: 0."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _parse_prm_score(text: str) -> Optional[int]:
    matches = _SCORE_RE.findall(text)
    if matches:
        val = int(matches[-1])
        if val in (1, -1, 0):
            return val
    matches = _BOXED_RE.findall(text)
    if matches:
        val = int(matches[-1])
        if val in (1, -1, 0):
            return val
    return None


def _majority_vote(scores: list[Optional[int]]) -> float:
    valid = [s for s in scores if s is not None]
    if not valid:
        return 0.0
    counter = collections.Counter(valid)
    top = counter.most_common(1)[0]
    if list(counter.values()).count(top[1]) > 1:
        return 0.0
    return float(top[0])


class PRMScorer:
    def __init__(
        self,
        prm_url: str,
        prm_model: str = "local-model",
        prm_m: int = 1,
        temperature: float = 0.6,
        max_new_tokens: int = 1024,
    ):
        self.prm_url = f"{prm_url.rstrip('/')}/chat/completions"
        self.prm_model = prm_model
        self.prm_m = prm_m
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens

    async def evaluate(
        self,
        response: str,
        instruction: str,
        session_id: str = "",
        turn_num: int = 0,
    ) -> dict:
        msgs = _build_prm_judge_prompt(response, instruction)

        results = await asyncio.gather(
            *[self._query_once(msgs, i) for i in range(self.prm_m)]
        )

        scores = [r[0] for r in results]
        final = _majority_vote(scores)

        representative = ""
        if final != 0.0:
            for s, text in results:
                if s is not None and s == int(final):
                    representative = text
                    break

        votes_display = [s if s is not None else "fail" for s in scores]
        logger.info(
            f"{_CYAN}[PRMScorer] session={session_id} turn={turn_num} "
            f"model={self.prm_model} votes={votes_display} → score={final}{_RESET}"
        )
        return {"score": final, "votes": votes_display, "eval_text": representative}

    async def _query_once(
        self, messages: list[dict], vote_id: int
    ) -> tuple[Optional[int], str]:
        try:
            payload = {
                "model": self.prm_model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_new_tokens,
            }
            # Use run_in_executor to make requests.post non-blocking for the event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(self.prm_url, json=payload, timeout=120)
            )
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content'] or ""
            return _parse_prm_score(content), content
        except Exception as e:
            logger.warning("[PRMScorer] query failed (vote %d): %s", vote_id, e)
            return None, ""
