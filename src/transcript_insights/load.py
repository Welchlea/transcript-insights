"""Read transcripts from a JSON Lines file. One conversation on each line."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

OUTCOMES = {"resolved", "handover", "abandoned"}
FALLBACK_STEP = "a fallback message"


@dataclass
class Turn:
    speaker: str                 # "user" or "bot"
    text: str
    intent: str | None = None    # user turns: what the bot thought the user wanted
    step: str | None = None      # bot turns: the name of the step that sent this message
    fallback: bool = False       # bot turns: true when the bot did not understand


@dataclass
class Conversation:
    id: str
    outcome: str
    turns: list[Turn] = field(default_factory=list)
    channel: str = ""

    @property
    def intent(self) -> str:
        """The first thing the bot recognised the user as wanting."""
        for turn in self.turns:
            if turn.speaker == "user" and turn.intent:
                return turn.intent
        return "not recognised"

    @property
    def fallbacks(self) -> int:
        return sum(1 for t in self.turns if t.speaker == "bot" and t.fallback)

    @property
    def last_bot_step(self) -> str:
        for turn in reversed(self.turns):
            if turn.speaker == "bot":
                if turn.fallback:
                    return FALLBACK_STEP
                return turn.step or "unknown"
        return "unknown"

    def unmatched_messages(self) -> list[str]:
        """User messages that the bot answered with a fallback."""
        found = []
        for before, after in zip(self.turns, self.turns[1:]):
            if before.speaker == "user" and after.speaker == "bot" and after.fallback:
                found.append(before.text)
        return found

    def longest_fallback_run(self) -> int:
        longest = run = 0
        for turn in self.turns:
            if turn.speaker != "bot":
                continue
            run = run + 1 if turn.fallback else 0
            longest = max(longest, run)
        return longest


def parse_conversation(data: dict) -> Conversation:
    outcome = str(data.get("outcome", ""))
    if outcome not in OUTCOMES:
        raise ValueError(f"Conversation {data.get('id')}: outcome must be one of {sorted(OUTCOMES)}")
    turns = [
        Turn(
            speaker=str(t["speaker"]),
            text=str(t.get("text", "")),
            intent=t.get("intent"),
            step=t.get("step"),
            fallback=bool(t.get("fallback", False)),
        )
        for t in data.get("turns") or []
    ]
    return Conversation(str(data["id"]), outcome, turns, str(data.get("channel", "")))


def load_transcripts(path: str | Path) -> list[Conversation]:
    conversations = []
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                conversations.append(parse_conversation(json.loads(line)))
            except (json.JSONDecodeError, KeyError) as error:
                raise ValueError(f"Line {number}: could not read conversation ({error})") from error
    return conversations
