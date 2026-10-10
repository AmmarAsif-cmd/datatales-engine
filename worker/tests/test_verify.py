"""Number checker tests. NUMBERS are FAKE but shaped like a real story's numbers."""

from decimal import Decimal

import pytest

from datatales.verify import allowed_from_numbers, extract_tokens, flatten_numbers, verify_text

NUMBERS = {
    "data_period": {"first": "2011-12", "last": "2022-23"},
    "findings": [
        {
            "group": "Fakeshire",
            "start_period": "2011-12",
            "end_period": "2022-23",
            "start_value": 34.11,
            "end_value": 39.53,
            "change": 5.42,
            "pct_change": 15.89,
            "start_rank": 4,
            "end_rank": 1,
            "groups_compared": 4,
            "unit": "average score out of 10",
            "median_change": -0.24,
            "good_news": True,
        }
    ],
    "series": [{"points": [{"period": "2020-21", "value": 35.94, "ci": [34.0, 37.88]}]}],
}


def check(**fields: str):  # noqa: ANN201
    return verify_text(fields, NUMBERS)


def test_real_numbers_pass_with_rounding_sign_and_formats() -> None:
    r = check(
        headline="Fakeshire wellbeing 2011–2023",
        hook="The share in Fakeshire rose from 34.1% to 39.5% between 2011-12 and 2022-23.",
        summary="That is 5.42 percentage points, a 16% rise, from 4th to 1st of four areas.",
        body_md="It dipped to 35.9 in 2020-21. The median fell by 0.24. Scores are out of 10.",
        video_script="Up 5.4 points since 2011.",
    )
    assert r.passed, r.unmatched + r.years_out_of_range
    assert r.checked >= 15


@pytest.mark.parametrize(
    "field",
    ["headline", "hook", "summary", "body_md", "video_script"],
)
def test_made_up_number_fails_in_every_field(field: str) -> None:
    r = check(**{field: "The share rose to 41.2% in Fakeshire."})
    assert not r.passed
    assert r.unmatched == [{"field": field, "text": "41.2%", "kind": "percent", "value": "41.2"}]


@pytest.mark.parametrize(
    "text",
    [
        "It rose by 6 percentage points.",  # 5.42 does not round to 6
        "Scores rose by 5.5 points.",  # wrong rounding of 5.42
        "Up 39.6%.",  # 39.53 rounds to 39.5, not 39.6
        "It is 2.5 times higher.",  # ratio not in NUMBERS
        "It climbed to 3rd place.",  # rank 3 not in NUMBERS
        "Around £1,200 per person.",  # money not in NUMBERS
        "Eleven areas were compared.",  # word number not in NUMBERS
        "A rise of 12,345 people.",
    ],
)
def test_invented_or_misrounded_numbers_fail(text: str) -> None:
    assert not check(body_md=text).passed


@pytest.mark.parametrize(
    "text",
    ["Back in 2009 it was lower.", "By 2030 it may change.", "Compared with 2023-24."],
)
def test_years_outside_data_period_fail(text: str) -> None:
    r = check(body_md=text)
    assert not r.passed and r.years_out_of_range and not r.unmatched


def test_years_inside_period_pass() -> None:
    assert check(body_md="From 2011 to 2023, and in 2020-21 and 2022–23.").passed


def test_extract_tokens_kinds() -> None:
    tokens = extract_tokens("f", "4th, 39.5%, £1,200, 2.5 times, 2020, 2011-12, twice, -0.24")
    kinds = [(t.text, t.kind) for t in tokens]
    assert kinds == [
        ("4th", "ordinal"),
        ("39.5%", "percent"),
        ("£1,200", "money"),
        ("2.5 times", "times"),
        ("2020", "year"),
        ("2011-12", "financial_year"),
        ("twice", "word"),
        ("-0.24", "number"),
    ]


def test_allowed_values_include_nested_numbers_period_years_and_scale() -> None:
    values, years = allowed_from_numbers(NUMBERS)
    assert {str(v) for v in values} >= {"34.11", "5.42", "0.24", "35.94", "37.88", "10"}
    assert years == {2011, 2012, 2020, 2021, 2022, 2023}


def test_booleans_are_not_numbers() -> None:
    values, _ = allowed_from_numbers({"good_news": True, "x": False})
    assert values == set()


def test_report_serialises() -> None:
    report = check(body_md="Up to 99.9%.").to_json()
    assert report["status"] == "failed" and report["unmatched"][0]["text"] == "99.9%"


# ---- claim-level verification ----


def test_flatten_numbers_gives_readable_keys() -> None:
    keys = flatten_numbers(NUMBERS)
    assert keys["f1.start_value"] == Decimal("34.11")
    assert keys["f1.groups_compared"] == 4
    assert keys["f1.scale_max"] == 10  # from "average score out of 10"
    assert keys["s1.points.2020-21.value"] == Decimal("35.94")
    assert keys["s1.points.2020-21.ci.lower"] == Decimal("34.0")
    assert "f1.good_news" not in keys  # booleans are not numbers


CLAIMED = "The share rose from 34.11% to 39.5%, the most of four areas."


def claim_check(text: str, claims: list[dict], field: str = "body_md"):  # noqa: ANN201
    return verify_text({field: text}, NUMBERS, claims)


def test_claim_ok() -> None:
    r = claim_check(
        CLAIMED,
        [{"sentence": CLAIMED, "keys": ["f1.start_value", "f1.end_value", "f1.groups_compared"]}],
    )
    assert r.passed and r.claims[0]["status"] == "ok"
    assert [n["key"] for n in r.claims[0]["numbers"]] == [
        "f1.start_value",
        "f1.end_value",
        "f1.groups_compared",
    ]


def test_claim_number_not_in_its_keys_is_a_mismatch() -> None:
    # 39.5 is real (end_value) but the claim only names start_value and groups_compared
    r = claim_check(
        CLAIMED, [{"sentence": CLAIMED, "keys": ["f1.start_value", "f1.groups_compared"]}]
    )
    assert not r.passed and not r.unmatched
    assert r.claims[0]["status"] == "mismatch"
    assert {"text": "39.5%", "key": None} in r.claims[0]["numbers"]


def test_claim_sentence_must_be_in_text() -> None:
    r = claim_check(
        CLAIMED, [{"sentence": "Something else with 34.11.", "keys": ["f1.start_value"]}]
    )
    assert r.claims[0]["status"] == "sentence_not_found"
    assert {u["text"] for u in r.uncovered} == {"34.11%", "39.5%", "four"}


def test_claim_unknown_key() -> None:
    r = claim_check(CLAIMED, [{"sentence": CLAIMED, "keys": ["f9.made_up"]}])
    assert r.claims[0]["status"] == "unknown_keys" and r.claims[0]["unknown_keys"] == ["f9.made_up"]


def test_numbers_outside_any_claim_are_uncovered() -> None:
    text = CLAIMED + " It dipped to 35.9 in 2020-21."
    keys = ["f1.start_value", "f1.end_value", "f1.groups_compared"]
    r = claim_check(text, [{"sentence": CLAIMED, "keys": keys}])
    assert not r.passed
    assert r.uncovered == [
        {"field": "body_md", "text": "35.9", "sentence": "It dipped to 35.9 in 2020-21."}
    ]


def test_claim_matching_ignores_markdown_spacing_and_quotes() -> None:
    text = "The **share** rose from 34.11%\nto  39.5%, the most of four areas."
    keys = ["f1.start_value", "f1.end_value", "f1.groups_compared"]
    assert claim_check(text, [{"sentence": CLAIMED, "keys": keys}]).passed


def test_one_claim_covers_the_same_sentence_in_two_fields() -> None:
    keys = ["f1.start_value", "f1.end_value", "f1.groups_compared"]
    r = verify_text(
        {"summary": CLAIMED, "body_md": CLAIMED}, NUMBERS, [{"sentence": CLAIMED, "keys": keys}]
    )
    assert r.passed and r.claims[0]["fields"] == ["body_md", "summary"]


def test_sentences_with_only_years_need_no_claim() -> None:
    assert claim_check("Data from 2011-12 to 2022-23.", []).passed
