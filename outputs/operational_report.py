"""
operational_report.py

Visualization helpers for seasonal RO operational planning reports.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm


OUTPUT_DIR = Path(__file__).parent.parent / "outputs"


def _ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def _set_dynamic_ylim(ax, values, margin_ratio: float = 0.10):
    data = np.asarray(values, dtype=float)
    data_min = float(np.nanmin(data))
    data_max = float(np.nanmax(data))
    data_range = data_max - data_min
    margin = data_range * margin_ratio if data_range else abs(data_max) * margin_ratio
    if margin == 0:
        margin = 1.0

    ax.set_ylim(data_min - margin, data_max + margin)


def plot_seasonal_risk_calendar(calendar_df, location_name: str):
    """
    Plot a monthly heatmap of scaling risk indicators.
    """
    output_dir = _ensure_output_dir()
    indicators = ["LSI_CaCO3", "SR_CaSO4", "SR_BaSO4", "SR_SrSO4", "SR_SiO2"]
    values = calendar_df.set_index("month").loc[range(1, 13), indicators].T
    color_scores = np.zeros_like(values.to_numpy(dtype=float))

    for row_index, indicator in enumerate(indicators):
        raw_values = values.loc[indicator].to_numpy(dtype=float)
        if indicator == "LSI_CaCO3":
            # LSI risk threshold is 0. Map -1..0..1 to green..yellow..red.
            color_scores[row_index] = np.clip(raw_values + 1.0, 0.0, 2.0)
        else:
            # SR risk threshold is 1. Map 0..1..3 to green..yellow..red.
            below_threshold = raw_values <= 1.0
            color_scores[row_index, below_threshold] = raw_values[below_threshold]
            color_scores[row_index, ~below_threshold] = 1.0 + np.clip(
                (raw_values[~below_threshold] - 1.0) / 2.0,
                0.0,
                1.0,
            )

    fig, ax = plt.subplots(figsize=(13, 4.8))
    norm = TwoSlopeNorm(vmin=0.0, vcenter=1.0, vmax=2.0)
    image = ax.imshow(
        color_scores,
        cmap="RdYlGn_r",
        norm=norm,
        aspect="auto",
    )

    ax.set_title(f"Seasonal Scaling Risk Calendar - {location_name}", pad=14)
    ax.set_xlabel("Month")
    ax.set_ylabel("Indicator")
    ax.set_xticks(np.arange(12), labels=[str(month) for month in range(1, 13)])
    ax.set_yticks(np.arange(len(indicators)), labels=indicators)

    for row_index, indicator in enumerate(indicators):
        for col_index, month in enumerate(range(1, 13)):
            value = values.loc[indicator, month]
            text_color = (
                "white"
                if color_scores[row_index, col_index] > 1.45
                else "black"
            )
            ax.text(
                col_index,
                row_index,
                f"{value:.2f}",
                ha="center",
                va="center",
                color=text_color,
                fontsize=9,
            )

    colorbar = fig.colorbar(image, ax=ax, fraction=0.025, pad=0.02)
    colorbar.set_label("Normalized risk: green=safe, yellow=threshold, red=high")

    fig.tight_layout()
    output_path = output_dir / "seasonal_risk_calendar.png"
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_operational_trends(calendar_df, location_name: str):
    """
    Plot monthly temperature, salinity, scaling, and CIP trends.
    """
    output_dir = _ensure_output_dir()
    months = calendar_df["month"]

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    fig.suptitle(f"Operational Trends - {location_name}", fontsize=14, y=0.98)

    ax_temp = axes[0]
    ax_salinity = ax_temp.twinx()
    temp_line = ax_temp.plot(
        months,
        calendar_df["temperature_c"],
        marker="o",
        color="#d95f02",
        label="Temperature (C)",
    )
    salinity_line = ax_salinity.plot(
        months,
        calendar_df["salinity_psu"],
        marker="s",
        color="#1b9e77",
        label="Salinity (PSU)",
    )
    ax_temp.set_ylabel("Temperature (C)")
    ax_salinity.set_ylabel("Salinity (PSU)")
    _set_dynamic_ylim(ax_temp, calendar_df["temperature_c"])
    _set_dynamic_ylim(ax_salinity, calendar_df["salinity_psu"])
    ax_temp.grid(True, alpha=0.25)
    lines = temp_line + salinity_line
    ax_temp.legend(
        lines,
        [line.get_label() for line in lines],
        loc="upper left",
        bbox_to_anchor=(1.08, 1.0),
    )

    ax_scaling = axes[1]
    ax_barium = ax_scaling.twinx()
    lsi_line = ax_scaling.plot(
        months,
        calendar_df["LSI_CaCO3"],
        marker="o",
        color="#7570b3",
        label="LSI CaCO3",
    )
    barium_line = ax_barium.plot(
        months,
        calendar_df["SR_BaSO4"],
        marker="s",
        color="#e7298a",
        label="SR BaSO4",
    )
    ax_scaling.axhline(0, color="#7570b3", linestyle="--", linewidth=1, alpha=0.5)
    ax_barium.axhline(1, color="#e7298a", linestyle="--", linewidth=1, alpha=0.5)
    ax_scaling.set_ylabel("LSI CaCO3")
    ax_barium.set_ylabel("SR BaSO4")
    _set_dynamic_ylim(ax_scaling, calendar_df["LSI_CaCO3"])
    _set_dynamic_ylim(ax_barium, calendar_df["SR_BaSO4"])
    ax_scaling.grid(True, alpha=0.25)
    lines = lsi_line + barium_line
    ax_scaling.legend(
        lines,
        [line.get_label() for line in lines],
        loc="upper left",
        bbox_to_anchor=(1.08, 1.0),
    )

    ax_days = axes[2]
    ax_cip = ax_days.twinx()
    days_line = ax_days.plot(
        months,
        calendar_df["days_to_cip"],
        marker="o",
        color="#1f78b4",
        label="Days to CIP",
    )
    cip_line = ax_cip.plot(
        months,
        calendar_df["cip_per_year"],
        marker="s",
        color="#e6ab02",
        label="CIP/year",
    )
    ax_days.set_ylabel("Days to CIP")
    ax_cip.set_ylabel("CIP/year")
    ax_days.set_xlabel("Month")
    _set_dynamic_ylim(ax_days, calendar_df["days_to_cip"])
    _set_dynamic_ylim(ax_cip, calendar_df["cip_per_year"])
    ax_days.grid(True, alpha=0.25)
    lines = days_line + cip_line
    ax_days.legend(
        lines,
        [line.get_label() for line in lines],
        loc="upper left",
        bbox_to_anchor=(1.08, 1.0),
    )

    axes[2].set_xticks(range(1, 13))
    fig.tight_layout()

    output_path = output_dir / "operational_trends.png"
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_opex_comparison(scenarios_results: dict, plant_capacity, location_name: str):
    """
    Plot stacked annual OPEX bars for multiple operating scenarios.
    """
    output_dir = _ensure_output_dir()
    components = [
        ("CIP chemicals", "cip_chemicals_eur", "#66c2a5"),
        ("Service water", "cip_service_water_eur", "#fc8d62"),
        ("Downtime", "cip_downtime_eur", "#8da0cb"),
        ("Antiscalant", "antiscalant_eur", "#e78ac3"),
        ("Membrane replacement", "membrane_replacement_eur", "#a6d854"),
    ]

    labels = list(scenarios_results.keys())
    x_positions = np.arange(len(labels))
    bottoms = np.zeros(len(labels))

    fig, ax = plt.subplots(figsize=(11, 6.5))
    for component_name, key, color in components:
        values = np.array([scenarios_results[label][key] for label in labels])
        ax.bar(
            x_positions,
            values,
            bottom=bottoms,
            label=component_name,
            color=color,
            edgecolor="white",
            linewidth=0.6,
        )
        bottoms += values

    for index, total in enumerate(bottoms):
        ax.text(
            index,
            total,
            f"{total:,.0f} EUR",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.set_title(
        f"Annual OPEX Comparison - {location_name} ({plant_capacity:,.0f} m3/day)",
        pad=14,
    )
    ax.set_ylabel("EUR/year")
    ax.set_xticks(x_positions, labels=labels)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0))
    ax.yaxis.set_major_formatter(lambda value, _: f"{value / 1000:,.0f}k")

    fig.tight_layout()
    output_path = output_dir / "opex_comparison.png"
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output_path
