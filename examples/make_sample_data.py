"""Make the made-up transcripts used in the example.

Nothing here comes from a real service. The script builds conversations
from a few patterns so the report has something realistic to find.
The same seed always gives the same file.

    python examples/make_sample_data.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

SEED = 7
COUNT = 400

# topic: (share of conversations, opening messages, steps, chance of each outcome)
TOPICS = {
    "check_balance": (
        0.28,
        ["How much is in my pension?", "what's my balance", "pension value please"],
        ["confirm_identity", "show_balance"],
        {"resolved": 0.88, "handover": 0.04, "abandoned": 0.08},
    ),
    "change_address": (
        0.18,
        ["I've moved house", "change my address", "new address"],
        ["confirm_identity", "ask_postcode", "confirm_address"],
        {"resolved": 0.80, "handover": 0.08, "abandoned": 0.12},
    ),
    "take_money_out": (
        0.22,
        ["I want to take money out", "can I withdraw my pension", "how do I get my money"],
        ["confirm_identity", "check_age", "explain_tax", "choose_amount"],
        {"resolved": 0.38, "handover": 0.17, "abandoned": 0.45},
    ),
    "report_death": (
        0.06,
        ["My husband has died", "my mum passed away and had a pension with you"],
        ["bereavement_handover"],
        {"resolved": 0.0, "handover": 1.0, "abandoned": 0.0},
    ),
    "complaint": (
        0.05,
        ["I want to complain", "this is a complaint"],
        ["complaint_handover"],
        {"resolved": 0.0, "handover": 1.0, "abandoned": 0.0},
    ),
}

# Messages the bot has not been taught. Weighted so a few come up often.
UNKNOWN = [
    ("Can I take a lump sum?", 9),
    ("can i take a lump sum", 6),
    ("transfer my pension to another provider", 8),
    ("Transfer my pension to another provider?", 3),
    ("what is my tax code", 6),
    ("is this a scam", 4),
    ("how do I add a beneficiary", 4),
    ("hello", 3),
    ("agent", 3),
]

STEP_TEXT = {
    "confirm_identity": "I need to check who you are. What is your date of birth?",
    "show_balance": "Your pension is worth £48,210 today.",
    "ask_postcode": "What is your new postcode?",
    "confirm_address": "Your new address starts 12 High Street. Is that right?",
    "check_age": "You can usually take money from age 55. How old are you?",
    "explain_tax": (
        "The first 25% of your pension is usually tax free. The rest is taxed as income "
        "at your marginal rate, which depends on your other income in the tax year, "
        "your personal allowance and any emergency tax code applied to the payment."
    ),
    "choose_amount": "How much do you want to take out?",
    "bereavement_handover": "I am sorry for your loss. I am passing you to one of our team.",
    "complaint_handover": "I am sorry something has gone wrong. I am passing you to one of our team.",
    "fallback": "Sorry, I did not understand. Can you say that another way?",
    "handover": "I am passing you to one of our team.",
    "done": "Is there anything else I can help with?",
}

# What the user says back at each step.
ANSWERS = {
    "confirm_identity": ["14 3 1975", "2 11 1968", "30 6 1982"],
    "ask_postcode": ["SR2 7AB", "NE1 4ST", "DH1 3LE"],
    "confirm_address": ["yes", "yes that's right"],
    "check_age": ["58", "61", "I'm 56"],
    "explain_tax": ["ok", "right", "ok thanks"],
    "choose_amount": ["£5,000", "all of it", "10000"],
}


def weighted(rng: random.Random, pairs):
    items, weights = zip(*pairs)
    return rng.choices(items, weights=weights)[0]


def bot(step: str, fallback: bool = False) -> dict:
    return {"speaker": "bot", "text": STEP_TEXT[step], "step": step, "fallback": fallback}


def known_conversation(rng: random.Random, topic: str) -> tuple[list[dict], str]:
    _, openers, steps, outcomes = TOPICS[topic]
    outcome = weighted(rng, outcomes.items())
    turns = [{"speaker": "user", "text": rng.choice(openers), "intent": topic}]

    if outcome == "abandoned":
        # Most people who leave the withdrawal journey leave at the tax message.
        if topic == "take_money_out" and rng.random() < 0.7:
            stop = steps.index("explain_tax")
        else:
            # Nobody is counted as leaving at the last step, where the task is done.
            stop = rng.randrange(max(len(steps) - 1, 1))
        steps = steps[: stop + 1]

    for index, step in enumerate(steps):
        turns.append(bot(step))
        last = index == len(steps) - 1
        if step.endswith("_handover") or (last and outcome == "abandoned"):
            break
        if step in ANSWERS:
            turns.append({"speaker": "user", "text": rng.choice(ANSWERS[step])})

    if outcome == "resolved":
        turns.append(bot("done"))
    elif outcome == "handover" and not steps[-1].endswith("_handover"):
        turns.append(bot("handover"))
    return turns, outcome


def unknown_conversation(rng: random.Random) -> tuple[list[dict], str]:
    """The bot does not recognise what the user wants."""
    message = weighted(rng, UNKNOWN)
    turns = [{"speaker": "user", "text": message, "intent": None}, bot("fallback", fallback=True)]
    roll = rng.random()
    if roll < 0.25:
        # The user rephrases into something the bot knows.
        topic = rng.choice(["check_balance", "take_money_out"])
        more, outcome = known_conversation(rng, topic)
        return turns + more, outcome
    if roll < 0.75:
        # The user tries again and gets a second fallback.
        turns.append({"speaker": "user", "text": weighted(rng, UNKNOWN), "intent": None})
        turns.append(bot("fallback", fallback=True))
        if rng.random() < 0.4:
            turns.append({"speaker": "user", "text": "speak to a person"})
            turns.append(bot("handover"))
            return turns, "handover"
        return turns, "abandoned"
    return turns, "abandoned"


def main() -> None:
    rng = random.Random(SEED)
    topic_weights = [(name, spec[0]) for name, spec in TOPICS.items()] + [("unknown", 0.21)]
    out = Path(__file__).parent / "transcripts.jsonl"
    with open(out, "w", encoding="utf-8") as handle:
        for number in range(1, COUNT + 1):
            topic = weighted(rng, topic_weights)
            if topic == "unknown":
                turns, outcome = unknown_conversation(rng)
            else:
                turns, outcome = known_conversation(rng, topic)
            record = {
                "id": f"c{number:04d}",
                "channel": rng.choice(["web", "web", "app"]),
                "outcome": outcome,
                "turns": turns,
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Wrote {COUNT} conversations to {out}")


if __name__ == "__main__":
    main()
