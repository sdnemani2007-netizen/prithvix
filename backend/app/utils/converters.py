import math
from typing import Any


def celsius_to_fahrenheit(c: float) -> float:
    return round((c * 9.0 / 5.0) + 32.0, 1)


def mm_to_inches(mm: float) -> float:
    return round(mm / 25.4, 2)


def hectares_to_acres(ha: float) -> float:
    return round(ha * 2.47105, 2)


def acres_to_hectares(acres: float) -> float:
    return round(acres / 2.47105, 2)


def json_safe(value: Any) -> Any:
    """Recursively convert NumPy/Pandas/dates to JSON-serializable types."""
    import numpy as np
    import pandas as pd
    from datetime import datetime, date

    if value is None:
        return None
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value
