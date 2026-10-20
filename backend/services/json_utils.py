"""
JSON-safety helpers.

Analysis pipelines can legitimately produce non-finite floats
(``nan``, ``inf``) and NumPy scalars from extreme inputs. Strict JSON
consumers reject ``NaN``/``Infinity`` tokens, and attempting to encode
them raises ``ValueError``, which previously surfaced as HTTP 500.
These helpers keep every response JSON-serialisable and finite.
"""

import math
from typing import Any

import numpy as np

_NUMPY_INTEGER = (np.integer,)
_NUMPY_FLOAT = (np.floating,)
_NUMPY_BOOL = (np.bool_,)
_NUMPY_STR = (np.str_,)


def safe_float(value: Any) -> float | None:
    """Return a finite float, or None for missing/non-finite values."""
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


def to_json_safe(value: Any) -> Any:
    """
    Recursively convert a value into strict-JSON-safe primitives.

    Non-finite floats become None, NumPy scalars become Python
    scalars, and containers are rebuilt recursively.
    """
    if isinstance(value, dict):
        return {str(key): to_json_safe(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [to_json_safe(item) for item in value]

    if isinstance(value, np.ndarray):
        return [to_json_safe(item) for item in value.tolist()]

    if isinstance(value, _NUMPY_BOOL):
        return bool(value)

    if isinstance(value, _NUMPY_INTEGER):
        return int(value)

    if isinstance(value, _NUMPY_FLOAT):
        return safe_float(value)

    if isinstance(value, _NUMPY_STR):
        return str(value)

    if isinstance(value, float):
        return safe_float(value)

    return value
