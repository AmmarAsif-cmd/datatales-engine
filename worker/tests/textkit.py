"""Builds narration bodies that satisfy the structure rules, for tests (FAKE text)."""

FILLER = (
    "These figures come from a large household survey and describe how people rated their "
    "own lives. They are estimates, so each one sits inside a range of likely values. "
)


def padded_body(core: str, words: int = 520) -> str:
    """`core` text, then the two required sections, padded with number-free filler."""
    compare = "## How it compares\n\n" + FILLER * 4
    limits = "## What the data can't tell us\n\n" + FILLER * 4
    body = f"{core}\n\n{compare}\n\n{limits}"
    while len(body.split()) < words:
        body += "\n\n" + FILLER
    return body
