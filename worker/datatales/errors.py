"""Errors the CLI reports as a one-line message (no traceback)."""


class UserError(Exception):
    """An expected problem the user can fix: bad input, missing data, failed validation."""
