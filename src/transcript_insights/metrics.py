"""Work out the measures a conversation designer uses to find problems."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from .load import FALLBACK_STEP, Conversation


def _rate(part: int, whole: int) -> float:
    return part / whole if whole else 0.0


@dataclass
class IntentStats:
    intent: str
    total: int = 0
    resolved: int = 0
    handover: int = 0
    abandoned: int = 0
    designed_handover: bool = False

    @property
    def resolved_rate(self) -> float:
        return _rate(self.resolved, self.total)

    @property
    def handover_rate(self) -> float:
        return _rate(self.handover, self.total)

    @property
    def abandoned_rate(self) -> float:
        return _rate(self.abandoned, self.total)


@dataclass
class Summary:
    total: int = 0
    resolved: int = 0
    handover: int = 0
    abandoned: int = 0
    designed_handovers: int = 0
    bot_turns: int = 0
    fallback_turns: int = 0
    conversations_with_fallback: int = 0
    repeated_fallback: int = 0
    repeated_fallback_lost: int = 0
    average_turns: float = 0.0
    intents: list[IntentStats] = field(default_factory=list)
    drop_off_steps: list[tuple[str, int]] = field(default_factory=list)
    unmatched: list[tuple[str, int]] = field(default_factory=list)

    @property
    def resolved_rate(self) -> float:
        return _rate(self.resolved, self.total)

    @property
    def handover_rate(self) -> float:
        return _rate(self.handover, self.total)

    @property
    def abandoned_rate(self) -> float:
        return _rate(self.abandoned, self.total)

    @property
    def fallback_rate(self) -> float:
        """Share of bot messages that were 'I did not understand'."""
        return _rate(self.fallback_turns, self.bot_turns)

    @property
    def containment_rate(self) -> float:
        """Resolved by the bot, out of conversations the bot was meant to handle.

        Some handovers are by design, for example a bereavement. Counting
        those as failures would push a team to keep vulnerable users in the bot.
        """
        return _rate(self.resolved, self.total - self.designed_handovers)

    @property
    def repeated_fallback_lost_rate(self) -> float:
        return _rate(self.repeated_fallback_lost, self.repeated_fallback)


def normalise(text: str) -> str:
    """Lower case and strip punctuation so near-identical messages group together."""
    return " ".join(re.sub(r"[^a-z0-9£ ]", " ", text.lower()).split())


def summarise(
    conversations: list[Conversation],
    designed_handover: set[str] | None = None,
    top: int = 5,
) -> Summary:
    designed = designed_handover or set()
    summary = Summary(total=len(conversations))
    by_intent: dict[str, IntentStats] = {}
    drop_off: Counter[str] = Counter()
    unmatched: Counter[str] = Counter()
    turn_count = 0

    for conv in conversations:
        turn_count += len(conv.turns)
        stats = by_intent.setdefault(
            conv.intent, IntentStats(conv.intent, designed_handover=conv.intent in designed)
        )
        stats.total += 1
        setattr(stats, conv.outcome, getattr(stats, conv.outcome) + 1)
        setattr(summary, conv.outcome, getattr(summary, conv.outcome) + 1)

        if conv.outcome == "handover" and conv.intent in designed:
            summary.designed_handovers += 1
        if conv.outcome == "abandoned":
            drop_off[conv.last_bot_step] += 1

        bot_turns = [t for t in conv.turns if t.speaker == "bot"]
        summary.bot_turns += len(bot_turns)
        summary.fallback_turns += conv.fallbacks
        if conv.fallbacks:
            summary.conversations_with_fallback += 1
        if conv.longest_fallback_run() >= 2:
            summary.repeated_fallback += 1
            if conv.outcome != "resolved":
                summary.repeated_fallback_lost += 1
        for message in conv.unmatched_messages():
            key = normalise(message)
            if key:
                unmatched[key] += 1

    summary.average_turns = round(_rate(turn_count, len(conversations)), 1)
    summary.intents = sorted(by_intent.values(), key=lambda s: (-s.total, s.intent))
    summary.drop_off_steps = drop_off.most_common(top)
    summary.unmatched = unmatched.most_common(top)
    return summary


def recommendations(summary: Summary, min_volume: int = 20) -> list[str]:
    """Plain language suggestions, worst problem first."""
    found: list[str] = []

    candidates = [
        s for s in summary.intents
        if s.total >= min_volume and not s.designed_handover and s.intent != "not recognised"
    ]
    if candidates:
        worst = max(candidates, key=lambda s: s.abandoned)
        if worst.abandoned_rate >= 0.2:
            found.append(
                f"Review the '{worst.intent}' journey. {worst.abandoned_rate:.0%} of users leave "
                f"without an answer ({worst.abandoned} of {worst.total})."
            )

    # Fallbacks are covered below, so look for the worst named step.
    named_steps = [(s, c) for s, c in summary.drop_off_steps if s != FALLBACK_STEP]
    if named_steps:
        step, count = named_steps[0]
        share = _rate(count, summary.abandoned)
        if share >= 0.2:
            found.append(
                f"Rewrite or split the '{step}' step. {share:.0%} of all abandoned "
                f"conversations end there ({count} of {summary.abandoned})."
            )

    if summary.unmatched:
        phrases = ", ".join(f'"{text}" ({count})' for text, count in summary.unmatched[:3])
        found.append(f"Teach the bot these messages, or add them to an existing topic: {phrases}.")

    if summary.repeated_fallback and summary.repeated_fallback_lost_rate >= 0.5:
        found.append(
            f"Offer a person after the first unclear answer. {summary.repeated_fallback} users got "
            f"two fallbacks in a row and {summary.repeated_fallback_lost_rate:.0%} of them did not "
            "get an answer from the bot."
        )

    unrecognised = next((s for s in summary.intents if s.intent == "not recognised"), None)
    if unrecognised and _rate(unrecognised.total, summary.total) >= 0.1:
        found.append(
            f"{_rate(unrecognised.total, summary.total):.0%} of conversations never matched a topic. "
            "Check the welcome message says what the bot can help with."
        )
    return found
