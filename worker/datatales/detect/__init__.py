"""Detectors: pure functions (df, meta) -> list[Finding], registered by name.

Importing this package registers the built-in detectors.
"""

from datatales.detect import change, outlier, rank  # noqa: F401  (registers detectors)
from datatales.detect.base import REGISTRY, DetectMeta, Finding, register

__all__ = ["REGISTRY", "DetectMeta", "Finding", "register"]
