from pathlib import Path
from typing import Any, Literal, Optional, overload

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = [
    "id",
    "month",
    "hour",
    "dep_time",
    "arr_time",
    "dep_delay",
    "arr_delay",
    "carrier",
    "name",
    "origin",
    "dest",
]

NUMERIC_COLUMNS = ["month", "hour", "dep_time", "arr_time", "dep_delay", "arr_delay"]
DELAY_MIN = -180
DELAY_MAX = 1440


def _assert_required_columns(df: pd.DataFrame) -> None:
    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f"Hianyzo oszlopok: {', '.join(missing)}")


def _normalize_codes(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for column in ["carrier", "origin", "dest"]:
        normalized[column] = normalized[column].astype("string").str.upper().str.strip()
    normalized["name"] = normalized["name"].astype("string").str.strip()
    return normalized


def _build_quality_masks(df: pd.DataFrame) -> dict[str, pd.Series]:
    masks: dict[str, pd.Series] = {}

    for column in NUMERIC_COLUMNS:
        original_notna = df[column].notna()
        df[column] = pd.to_numeric(df[column], errors="coerce")
        masks[f"invalid_{column}_type"] = original_notna & df[column].isna()

    masks["missing_dep_time"] = df["dep_time"].isna()
    masks["missing_arr_time"] = df["arr_time"].isna()
    masks["missing_dep_delay"] = df["dep_delay"].isna()
    masks["missing_arr_delay"] = df["arr_delay"].isna()
    masks["missing_hour"] = df["hour"].isna()
    masks["missing_month"] = df["month"].isna()
    masks["missing_origin"] = df["origin"].isna()
    masks["missing_dest"] = df["dest"].isna()
    masks["missing_carrier"] = df["carrier"].isna()
    masks["missing_name"] = df["name"].isna()

    masks["invalid_hour_range"] = df["hour"].notna() & ~df["hour"].between(0, 23, inclusive="both")
    masks["invalid_hour_integer"] = df["hour"].notna() & (df["hour"] % 1 != 0)
    masks["invalid_month_range"] = df["month"].notna() & ~df["month"].between(1, 12, inclusive="both")
    masks["invalid_month_integer"] = df["month"].notna() & (df["month"] % 1 != 0)
    masks["invalid_dep_delay_range"] = df["dep_delay"].notna() & ~df["dep_delay"].between(DELAY_MIN, DELAY_MAX, inclusive="both")
    masks["invalid_arr_delay_range"] = df["arr_delay"].notna() & ~df["arr_delay"].between(DELAY_MIN, DELAY_MAX, inclusive="both")
    masks["invalid_origin_code"] = (
        df["origin"].notna()
        & ~df["origin"].str.fullmatch(r"[A-Z]{3}").fillna(False)
    )
    masks["invalid_dest_code"] = (
        df["dest"].notna()
        & ~df["dest"].str.fullmatch(r"[A-Z]{3}").fillna(False)
    )
    masks["invalid_carrier_code"] = (
        df["carrier"].notna()
        & ~df["carrier"].str.fullmatch(r"[A-Z0-9]{2}").fillna(False)
    )

    return masks


@overload
def load_and_clean_data(
    file_path: Optional[str] = None,
    return_report: Literal[False] = False,
) -> pd.DataFrame:
    ...


@overload
def load_and_clean_data(
    file_path: Optional[str] = None,
    return_report: Literal[True] = True,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    ...


def load_and_clean_data(
    file_path: Optional[str] = None,
    return_report: bool = False,
) -> pd.DataFrame | tuple[pd.DataFrame, dict[str, Any]]:
    target_path: Path

    if file_path is None:
        base_path = Path(__file__).resolve().parent.parent
        target_path = base_path / "data" / "raw" / "flights.csv"
    else:
        target_path = Path(file_path)

    if not target_path.exists():
        raise FileNotFoundError(f"Target path not exists: {target_path}")

    print(f"Adatok betoltese: {target_path} ...")
    df = pd.read_csv(target_path)
    _assert_required_columns(df)
    df = _normalize_codes(df)

    quality_masks = _build_quality_masks(df)
    invalid_row_mask = np.zeros(len(df), dtype=bool)
    for mask in quality_masks.values():
        invalid_row_mask |= mask.to_numpy(dtype=bool)

    total_rows = len(df)
    invalid_count = int(invalid_row_mask.sum())
    valid_count = int(total_rows - invalid_count)
    print(f"Tisztitas kesz: {invalid_count} db jarat torlodott")
    if invalid_count > 0:
        print("Torles okai:")
        for reason, mask in quality_masks.items():
            count = int(mask.sum())
            if count > 0:
                print(f" - {reason}: {count} sor")

    df = df.loc[~invalid_row_mask].copy()
    df["month"] = df["month"].astype(int)
    df["hour"] = df["hour"].astype(int)

    conditions = [
        (df["hour"] >= 0) & (df["hour"] < 6),
        (df["hour"] >= 6) & (df["hour"] < 12),
        (df["hour"] >= 12) & (df["hour"] < 18),
        (df["hour"] >= 18) & (df["hour"] <= 23),
    ]
    choices = ["Hajnal", "Delelott", "Delutan", "Este"]
    df["napszak"] = np.select(conditions, choices, default="Ismeretlen napszak")

    quality_report = {
        "total_rows": int(total_rows),
        "valid_rows": int(valid_count),
        "dropped_rows": int(invalid_count),
        "drop_rate_pct": float(np.round((invalid_count / total_rows) * 100, 2)) if total_rows > 0 else 0.0,
        "reason_counts": {
            reason: int(mask.sum())
            for reason, mask in quality_masks.items()
            if int(mask.sum()) > 0
        },
        "note": "A torlesi okok soronkent atfedhetnek, ezert a reszokok osszege nagyobb lehet.",
    }

    if return_report:
        return df, quality_report
    return df

if __name__ == "__main__":
    try:
        test_df = load_and_clean_data(return_report=False)
        print("\nSikeres a betoltes es a tipusellenorzes")
        print(test_df[["carrier", "origin", "dest", "napszak", "arr_delay"]].head())
    except Exception as e:
        print(f"\nHiba tortent: {e}")
