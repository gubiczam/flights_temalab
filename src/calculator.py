import numpy as np
import pandas as pd

MONTH_LABELS = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}

BAYES_PRIOR_STRENGTH = 40.0
CI_Z_SCORE = 1.96


def _fmt_number(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _fmt_percent(value: float) -> str:
    return f"{_fmt_number(value)}%"


def _fmt_pp(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{_fmt_number(value)} p.p."


def _bayesian_delay_risk(
    delayed_counts: np.ndarray,
    total_counts: np.ndarray,
    prior_mean: float,
    prior_strength: float = BAYES_PRIOR_STRENGTH,
) -> np.ndarray:
    alpha = prior_mean * prior_strength
    denominator = total_counts + prior_strength
    return np.divide(
        delayed_counts + alpha,
        denominator,
        out=np.zeros_like(delayed_counts, dtype=float),
        where=denominator > 0,
    ) * 100


def _wilson_interval(
    delayed_counts: np.ndarray,
    total_counts: np.ndarray,
    z_score: float = CI_Z_SCORE,
) -> tuple[np.ndarray, np.ndarray]:
    lower = np.zeros_like(delayed_counts, dtype=float)
    upper = np.zeros_like(delayed_counts, dtype=float)

    valid = total_counts > 0
    if not np.any(valid):
        return lower, upper

    n = total_counts[valid].astype(float)
    k = delayed_counts[valid].astype(float)
    p = k / n
    z2 = z_score ** 2

    denominator = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denominator
    margin = (
        z_score
        * np.sqrt((p * (1 - p) + z2 / (4 * n)) / n)
        / denominator
    )

    lower[valid] = np.clip((center - margin) * 100, 0, 100)
    upper[valid] = np.clip((center + margin) * 100, 0, 100)
    return lower, upper


def calculate_reliability(df: pd.DataFrame) -> pd.DataFrame:
    working_df = df.copy()
    working_df["is_delayed"] = (working_df["arr_delay"] > 15).astype(int)

    stats = working_df.groupby(["origin", "dest", "carrier", "name", "napszak"]).agg(
        osszes_jarat=("id", "count"),
        kesett_jaratok=("is_delayed", "sum"),
        atlagos_keses=("arr_delay", "mean"),
    ).reset_index()

    delayed_counts = stats["kesett_jaratok"].to_numpy(dtype=float)
    total_counts = stats["osszes_jarat"].to_numpy(dtype=float)

    global_delay_rate = float(working_df["is_delayed"].mean())
    stats["kesesi_esely_nyers"] = np.round(delayed_counts / total_counts * 100, 1)
    stats["kesesi_esely"] = np.round(
        _bayesian_delay_risk(delayed_counts, total_counts, global_delay_rate),
        1,
    )
    ci_lower, ci_upper = _wilson_interval(delayed_counts, total_counts)
    stats["kesesi_ci_lower"] = np.round(ci_lower, 1)
    stats["kesesi_ci_upper"] = np.round(ci_upper, 1)
    stats["atlagos_keses"] = np.round(stats["atlagos_keses"], 1)
    stats["score"] = np.round(100 - stats["kesesi_esely"], 1)

    return stats.sort_values(by=["origin", "dest", "score"], ascending=[True, True, False])


def calculate_global_baseline(df: pd.DataFrame) -> dict:
    global_delay_risk = float(np.round((df["arr_delay"] > 15).mean() * 100, 1))
    global_avg_delay = float(np.round(df["arr_delay"].mean(), 1))

    return {
        "global_kesesi_esely": global_delay_risk,
        "global_atlagos_keses": global_avg_delay,
        "global_flights": int(len(df)),
    }


def calculate_route_baseline(df_route: pd.DataFrame, global_baseline: dict) -> dict:
    route_delay_risk = float(np.round((df_route["arr_delay"] > 15).mean() * 100, 1))
    route_avg_delay = float(np.round(df_route["arr_delay"].mean(), 1))

    return {
        "global_kesesi_esely": global_baseline["global_kesesi_esely"],
        "global_atlagos_keses": global_baseline["global_atlagos_keses"],
        "global_flights": global_baseline["global_flights"],
        "route_kesesi_esely": route_delay_risk,
        "route_atlagos_keses": route_avg_delay,
        "route_flights": int(len(df_route)),
        "route_vs_global_pp": float(np.round(global_baseline["global_kesesi_esely"] - route_delay_risk, 1)),
    }


def calculate_monthly_seasonality(df_route: pd.DataFrame) -> list[dict]:
    monthly = (
        df_route.assign(is_delayed=(df_route["arr_delay"] > 15).astype(int))
        .groupby("month")
        .agg(
            osszes_jarat=("id", "count"),
            kesett_jaratok=("is_delayed", "sum"),
            atlagos_keses=("arr_delay", "mean"),
        )
        .reset_index()
    )

    monthly["kesesi_esely"] = np.round(monthly["kesett_jaratok"] / monthly["osszes_jarat"] * 100, 1)
    monthly["atlagos_keses"] = np.round(monthly["atlagos_keses"], 1)

    all_months = pd.DataFrame({"month": np.arange(1, 13, dtype=int)})
    monthly = all_months.merge(monthly, on="month", how="left")
    monthly["month_label"] = monthly["month"].map(MONTH_LABELS)

    monthly["osszes_jarat"] = monthly["osszes_jarat"].fillna(0).astype(int)
    monthly["kesesi_esely"] = monthly["kesesi_esely"].where(monthly["kesesi_esely"].notna(), None)
    monthly["atlagos_keses"] = monthly["atlagos_keses"].where(monthly["atlagos_keses"].notna(), None)

    return monthly[
        ["month", "month_label", "osszes_jarat", "kesesi_esely", "atlagos_keses"]
    ].to_dict(orient="records")


def _carrier_boxplot_stats(df_route: pd.DataFrame, min_samples: int) -> list[dict]:
    stats = []

    grouped = df_route.groupby(["carrier", "name"], dropna=False)
    for (carrier, name), group in grouped:
        delays = group["arr_delay"].dropna().astype(float).to_numpy()
        sample_size = int(delays.size)

        if sample_size < min_samples:
            continue

        q1, median, q3 = np.percentile(delays, [25, 50, 75])
        iqr = q3 - q1

        lower_limit = q1 - 1.5 * iqr
        upper_limit = q3 + 1.5 * iqr

        trimmed = delays[(delays >= lower_limit) & (delays <= upper_limit)]
        if trimmed.size == 0:
            trimmed = delays

        stats.append(
            {
                "carrier": str(carrier),
                "name": str(name),
                "sample_size": sample_size,
                "mean": float(np.round(np.mean(delays), 1)),
                "q1": float(np.round(q1, 1)),
                "median": float(np.round(median, 1)),
                "q3": float(np.round(q3, 1)),
                "min": float(np.round(np.min(trimmed), 1)),
                "max": float(np.round(np.max(trimmed), 1)),
            }
        )

    stats.sort(key=lambda item: (item["median"], -item["sample_size"]))
    return stats[:10]


def calculate_carrier_boxplot(df_route: pd.DataFrame) -> list[dict]:
    stats = _carrier_boxplot_stats(df_route, min_samples=25)
    if stats:
        return stats
    return _carrier_boxplot_stats(df_route, min_samples=8)


def build_dashboard_payload(
    recommendations: pd.DataFrame,
    baseline: dict,
    seasonality: list[dict],
    boxplot: list[dict],
    analytics_population: pd.DataFrame | None = None,
) -> dict:
    recommendations_view = recommendations.copy().reset_index(drop=True)

    recommendations_view["is_top"] = recommendations_view.index.to_numpy() == 0

    delay_values = recommendations_view["atlagos_keses"].to_numpy(dtype=float)
    early_minutes = np.round(np.abs(delay_values), 1)

    delay_classes = np.select(
        [delay_values < 0, delay_values > 0],
        ["early", "late"],
        default="neutral",
    )
    delay_labels = np.select(
        [delay_values < 0, delay_values == 0, delay_values > 0],
        [
            np.array([f"{_fmt_number(value)} perccel korabbi erkezes" for value in early_minutes], dtype=object),
            "Pontos erkezes",
            np.array([f"{_fmt_number(value)} perc keses" for value in np.round(delay_values, 1)], dtype=object),
        ],
    )

    recommendations_view["delay_class"] = delay_classes
    recommendations_view["delay_label"] = delay_labels

    route_delta_pp = np.round(baseline["route_kesesi_esely"] - recommendations_view["kesesi_esely"].to_numpy(dtype=float), 1)
    recommendations_view["route_delta_pp"] = route_delta_pp
    recommendations_view["route_delta_class"] = np.where(route_delta_pp >= 0, "positive", "negative")
    recommendations_view["route_delta_label"] = [
        _fmt_pp(float(value)) for value in route_delta_pp
    ]

    recommendations_view["kesesi_esely_label"] = [
        _fmt_percent(float(value)) for value in recommendations_view["kesesi_esely"].to_numpy(dtype=float)
    ]
    recommendations_view["kesesi_ci_label"] = [
        f"CI95: {_fmt_percent(float(lower))} - {_fmt_percent(float(upper))}"
        for lower, upper in zip(
            recommendations_view["kesesi_ci_lower"].to_numpy(dtype=float),
            recommendations_view["kesesi_ci_upper"].to_numpy(dtype=float),
        )
    ]

    best_vs_route_pp = float(route_delta_pp[0]) if route_delta_pp.size > 0 else 0.0

    baseline_view = {
        **baseline,
        "route_kesesi_esely_label": _fmt_percent(float(baseline["route_kesesi_esely"])),
        "global_kesesi_esely_label": _fmt_percent(float(baseline["global_kesesi_esely"])),
        "route_vs_global_label": _fmt_pp(float(baseline["route_vs_global_pp"])),
        "route_vs_global_class": "positive" if baseline["route_vs_global_pp"] >= 0 else "negative",
        "best_vs_route_pp": best_vs_route_pp,
        "best_vs_route_label": _fmt_pp(best_vs_route_pp),
        "best_vs_route_class": "positive" if best_vs_route_pp >= 0 else "negative",
    }

    risk_values = recommendations_view["kesesi_esely"].to_numpy(dtype=float)
    risk_colors = np.select(
        [risk_values < 15, risk_values < 30],
        ["#34a853", "#fbbc04"],
        default="#ea4335",
    )

    risk_chart = {
        "labels": [
            f"{carrier} ({period})"
            for carrier, period in zip(
                recommendations_view["carrier"].astype(str),
                recommendations_view["napszak"].astype(str),
            )
        ],
        "values": [float(value) for value in risk_values],
        "colors": [str(color) for color in risk_colors],
        "ci_lower": [
            float(value) for value in recommendations_view["kesesi_ci_lower"].to_numpy(dtype=float)
        ],
        "ci_upper": [
            float(value) for value in recommendations_view["kesesi_ci_upper"].to_numpy(dtype=float)
        ],
    }

    tradeoff_source = analytics_population.copy() if analytics_population is not None else recommendations_view.copy()
    tradeoff_source = tradeoff_source.reset_index(drop=True)
    tradeoff_source["is_top5"] = False
    if not tradeoff_source.empty:
        top_keys = set(
            zip(
                recommendations_view["carrier"].astype(str),
                recommendations_view["napszak"].astype(str),
            )
        )
        tradeoff_source["is_top5"] = [
            (carrier, napszak) in top_keys
            for carrier, napszak in zip(
                tradeoff_source["carrier"].astype(str),
                tradeoff_source["napszak"].astype(str),
            )
        ]

    tradeoff_sizes = tradeoff_source["osszes_jarat"].to_numpy(dtype=float)
    if tradeoff_sizes.size > 0 and float(np.max(tradeoff_sizes)) > float(np.min(tradeoff_sizes)):
        radii = np.interp(tradeoff_sizes, (np.min(tradeoff_sizes), np.max(tradeoff_sizes)), (5.0, 15.0))
    else:
        radii = np.full(shape=tradeoff_sizes.shape, fill_value=9.0)

    tradeoff_points = [
        {
            "x": float(row["kesesi_esely"]),
            "y": float(row["atlagos_keses"]),
            "r": float(np.round(radius, 1)),
            "carrier": str(row["carrier"]),
            "name": str(row["name"]),
            "napszak": str(row["napszak"]),
            "sample_size": int(row["osszes_jarat"]),
            "score": float(row["score"]),
            "is_top5": bool(row["is_top5"]),
        }
        for row, radius in zip(tradeoff_source.to_dict(orient="records"), radii)
    ]

    tradeoff_chart = {
        "points": tradeoff_points,
    }

    seasonality_df = pd.DataFrame(seasonality)
    punctuality = np.where(
        seasonality_df["kesesi_esely"].isna(),
        np.nan,
        np.round(100 - seasonality_df["kesesi_esely"].astype(float), 1),
    )

    seasonality_chart = {
        "labels": seasonality_df["month_label"].astype(str).tolist(),
        "punctuality": [None if np.isnan(value) else float(value) for value in punctuality],
        "avg_delay": [
            None if pd.isna(value) else float(value)
            for value in seasonality_df["atlagos_keses"].tolist()
        ],
    }

    boxplot_chart = {
        "labels": [item["carrier"] for item in boxplot],
        "stats": boxplot,
        "iqr": [[item["q1"], item["q3"]] for item in boxplot],
        "median": [item["median"] for item in boxplot],
        "mean": [item["mean"] for item in boxplot],
    }

    display_columns = [
        "carrier",
        "name",
        "napszak",
        "origin",
        "dest",
        "score",
        "osszes_jarat",
        "kesesi_esely",
        "kesesi_esely_nyers",
        "kesesi_ci_lower",
        "kesesi_ci_upper",
        "atlagos_keses",
        "is_top",
        "delay_class",
        "delay_label",
        "route_delta_pp",
        "route_delta_class",
        "route_delta_label",
        "kesesi_esely_label",
        "kesesi_ci_label",
    ]

    return {
        "baseline": baseline_view,
        "recommendations": recommendations_view[display_columns].to_dict(orient="records"),
        "charts": {
            "risk": risk_chart,
            "seasonality": seasonality_chart,
            "boxplot": boxplot_chart,
            "tradeoff": tradeoff_chart,
        },
    }
