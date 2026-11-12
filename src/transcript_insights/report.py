"""Write the summary as a Markdown report or as JSON."""

from __future__ import annotations

import json

from .metrics import Summary, recommendations


def _pct(value: float) -> str:
    return f"{value:.0%}"


def to_markdown(summary: Summary, title: str = "Chatbot transcript report") -> str:
    lines = [
        f"# {title}",
        "",
        f"{summary.total} conversations.",
        "",
        "## What to fix first",
        "",
    ]
    tips = recommendations(summary)
    if tips:
        lines += [f"{n}. {tip}" for n, tip in enumerate(tips, start=1)]
    else:
        lines.append("Nothing stands out. Keep watching the measures below.")

    lines += [
        "",
        "## Headline measures",
        "",
        "| Measure | Value | What it means |",
        "| --- | --- | --- |",
        f"| Containment | {_pct(summary.containment_rate)} | Resolved by the bot, leaving out handovers that are by design |",
        f"| Resolved | {_pct(summary.resolved_rate)} | The user got what they came for from the bot |",
        f"| Handed over | {_pct(summary.handover_rate)} | Passed to a person. {summary.designed_handovers} of {summary.handover} were by design |",
        f"| Abandoned | {_pct(summary.abandoned_rate)} | The user left part way through |",
        f"| Fallback rate | {_pct(summary.fallback_rate)} | Bot messages that were 'I did not understand' |",
        f"| Average length | {summary.average_turns} | Messages in a conversation, from both sides |",
        "",
        "## By topic",
        "",
        "| Topic | Conversations | Resolved | Handed over | Abandoned |",
        "| --- | --- | --- | --- | --- |",
    ]
    for stats in summary.intents:
        note = " (by design)" if stats.designed_handover else ""
        lines.append(
            f"| {stats.intent} | {stats.total} | {_pct(stats.resolved_rate)} | "
            f"{_pct(stats.handover_rate)}{note} | {_pct(stats.abandoned_rate)} |"
        )

    lines += ["", "## Where users give up", "", "| Last bot step before the user left | Conversations |", "| --- | --- |"]
    lines += [f"| {step} | {count} |" for step, count in summary.drop_off_steps]

    lines += ["", "## What the bot did not understand", "", "| User message | Times |", "| --- | --- |"]
    lines += [f"| {text} | {count} |" for text, count in summary.unmatched]

    lines += [
        "",
        "## Repeated fallbacks",
        "",
        f"{summary.repeated_fallback} conversations had two or more fallbacks in a row. "
        f"{_pct(summary.repeated_fallback_lost_rate)} of those were not resolved by the bot.",
    ]
    return "\n".join(lines) + "\n"


def to_json(summary: Summary) -> str:
    payload = {
        "total": summary.total,
        "containment_rate": round(summary.containment_rate, 4),
        "resolved_rate": round(summary.resolved_rate, 4),
        "handover_rate": round(summary.handover_rate, 4),
        "abandoned_rate": round(summary.abandoned_rate, 4),
        "fallback_rate": round(summary.fallback_rate, 4),
        "average_turns": summary.average_turns,
        "designed_handovers": summary.designed_handovers,
        "repeated_fallback": summary.repeated_fallback,
        "intents": [
            {
                "intent": s.intent,
                "total": s.total,
                "resolved": s.resolved,
                "handover": s.handover,
                "abandoned": s.abandoned,
                "designed_handover": s.designed_handover,
            }
            for s in summary.intents
        ],
        "drop_off_steps": [{"step": s, "count": c} for s, c in summary.drop_off_steps],
        "unmatched": [{"text": t, "count": c} for t, c in summary.unmatched],
        "recommendations": recommendations(summary),
    }
    return json.dumps(payload, indent=2)
