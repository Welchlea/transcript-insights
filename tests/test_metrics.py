import json
from pathlib import Path

import pytest

from transcript_insights.cli import main
from transcript_insights.load import FALLBACK_STEP, load_transcripts, parse_conversation
from transcript_insights.metrics import normalise, recommendations, summarise
from transcript_insights.report import to_json, to_markdown

EXAMPLES = Path(__file__).parent.parent / "examples"


def user(text, intent=None):
    return {"speaker": "user", "text": text, "intent": intent}


def bot(step, fallback=False):
    return {"speaker": "bot", "text": "...", "step": step, "fallback": fallback}


def conv(cid, outcome, turns):
    return parse_conversation({"id": cid, "outcome": outcome, "turns": turns})


RESOLVED = conv("1", "resolved", [user("balance", "check_balance"), bot("show_balance")])
BEREAVED = conv("2", "handover", [user("my husband died", "report_death"), bot("bereavement_handover")])
LOST = conv(
    "3",
    "abandoned",
    [
        user("Lump sum?"),
        bot("fallback", fallback=True),
        user("lump sum"),
        bot("fallback", fallback=True),
    ],
)
GAVE_UP = conv("4", "abandoned", [user("take money", "take_money_out"), bot("explain_tax")])


def test_intent_is_the_first_one_recognised():
    assert RESOLVED.intent == "check_balance"
    assert LOST.intent == "not recognised"


def test_unmatched_messages_are_the_ones_before_a_fallback():
    assert LOST.unmatched_messages() == ["Lump sum?", "lump sum"]
    assert RESOLVED.unmatched_messages() == []


def test_longest_fallback_run():
    assert LOST.longest_fallback_run() == 2
    assert GAVE_UP.longest_fallback_run() == 0


def test_last_bot_step_names_fallbacks_clearly():
    assert LOST.last_bot_step == FALLBACK_STEP
    assert GAVE_UP.last_bot_step == "explain_tax"


def test_normalise_groups_near_identical_messages():
    assert normalise("Lump sum?") == normalise("lump  SUM") == "lump sum"


def test_headline_rates():
    summary = summarise([RESOLVED, BEREAVED, LOST, GAVE_UP])
    assert summary.total == 4
    assert summary.resolved_rate == 0.25
    assert summary.handover_rate == 0.25
    assert summary.abandoned_rate == 0.5
    assert summary.fallback_rate == 2 / 5
    assert summary.unmatched == [("lump sum", 2)]
    assert summary.repeated_fallback == 1
    assert summary.repeated_fallback_lost_rate == 1.0


def test_designed_handovers_do_not_count_against_containment():
    plain = summarise([RESOLVED, BEREAVED])
    designed = summarise([RESOLVED, BEREAVED], designed_handover={"report_death"})
    assert plain.containment_rate == 0.5
    assert designed.containment_rate == 1.0
    assert designed.designed_handovers == 1


def test_drop_off_counts_only_abandoned_conversations():
    summary = summarise([RESOLVED, LOST, GAVE_UP])
    assert dict(summary.drop_off_steps) == {FALLBACK_STEP: 1, "explain_tax": 1}


def test_empty_file_gives_zero_rates_not_an_error():
    summary = summarise([])
    assert summary.containment_rate == 0.0
    assert recommendations(summary) == []


def test_recommendations_name_the_worst_journey_and_step():
    many = [GAVE_UP] * 15 + [conv("r", "resolved", [user("take money", "take_money_out"), bot("done")])] * 10
    tips = recommendations(summarise(many))
    assert tips[0].startswith("Review the 'take_money_out' journey. 60%")
    assert "'explain_tax'" in tips[1]


def test_recommendations_do_not_blame_designed_handovers():
    tips = recommendations(summarise([BEREAVED] * 30, designed_handover={"report_death"}))
    assert tips == []


def test_bad_outcome_is_an_error():
    with pytest.raises(ValueError, match="outcome"):
        parse_conversation({"id": "x", "outcome": "won", "turns": []})


def test_bad_line_reports_its_line_number(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"id": "1", "outcome": "resolved", "turns": []}\nnot json\n', encoding="utf-8")
    with pytest.raises(ValueError, match="Line 2"):
        load_transcripts(path)


def test_example_data_tells_the_expected_story():
    conversations = load_transcripts(EXAMPLES / "transcripts.jsonl")
    summary = summarise(conversations, designed_handover={"report_death", "complaint"})
    assert summary.total == 400
    assert summary.unmatched[0][0] == "can i take a lump sum"
    tips = recommendations(summary)
    assert "take_money_out" in tips[0]
    assert "explain_tax" in tips[1]


def test_reports_render():
    summary = summarise([RESOLVED, BEREAVED, LOST, GAVE_UP], designed_handover={"report_death"})
    markdown = to_markdown(summary)
    assert "## What to fix first" in markdown
    assert "100% (by design)" in markdown
    assert json.loads(to_json(summary))["total"] == 4


def test_cli_writes_a_report(tmp_path, capsys):
    out = tmp_path / "report.md"
    assert main([str(EXAMPLES / "transcripts.jsonl"), "--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8").startswith("# Chatbot transcript report")
    capsys.readouterr()
