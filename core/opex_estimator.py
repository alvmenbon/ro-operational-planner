"""
opex_estimator.py

Estimacion simple de OPEX anual para plantas SWRO a partir del calendario
operacional estacional.
"""

DEFAULT_COSTS = {
    "chemicals_per_cip_eur": 2500,
    "service_water_per_cip_m3": 6000,
    "service_water_cost_eur_m3": 0.5,
    "downtime_hours_per_cip": 4,
    "downtime_cost_eur_h": 500,
    "membrane_replacement_eur": 400,
    "membrane_lifetime_base_years": 5,
    "antiscalant_eur_per_m3_feed": 0.02,
}


def estimate_annual_opex(
    calendar_df,
    plant_capacity_m3_per_day: float,
    total_membrane_elements: int,
    costs: dict | None = None,
) -> dict:
    """
    Estimate annual OPEX from an operational calendar.

    Parameters
    ----------
    calendar_df : pandas.DataFrame
        Output from ``generate_operational_calendar``. Must include
        ``cip_per_year``.
    plant_capacity_m3_per_day : float
        Plant feed capacity in m3/day.
    total_membrane_elements : int
        Total installed SWRO membrane elements.
    costs : dict, optional
        Cost overrides. Missing keys fall back to ``DEFAULT_COSTS``.

    Returns
    -------
    dict
        Annual OPEX components in EUR plus operating assumptions used in
        the calculation.
    """
    cost_model = DEFAULT_COSTS.copy()
    if costs is not None:
        cost_model.update(costs)

    cip_per_year = float(calendar_df["cip_per_year"].mean())

    cip_chemicals_eur = cip_per_year * cost_model["chemicals_per_cip_eur"]
    cip_service_water_eur = (
        cip_per_year
        * cost_model["service_water_per_cip_m3"]
        * cost_model["service_water_cost_eur_m3"]
    )
    cip_downtime_eur = (
        cip_per_year
        * cost_model["downtime_hours_per_cip"]
        * cost_model["downtime_cost_eur_h"]
    )
    antiscalant_eur = (
        plant_capacity_m3_per_day
        * 365
        * cost_model["antiscalant_eur_per_m3_feed"]
    )

    base_lifetime = cost_model["membrane_lifetime_base_years"]
    extra_cip = max(0.0, cip_per_year - 4.0)
    lifetime_reduction = 0.10 * extra_cip
    adjusted_lifetime_years = base_lifetime * max(0.1, 1 - lifetime_reduction)

    total_membrane_replacement_cost = (
        total_membrane_elements * cost_model["membrane_replacement_eur"]
    )
    membrane_replacement_eur = (
        total_membrane_replacement_cost / adjusted_lifetime_years
    )

    total_opex_eur = (
        cip_chemicals_eur
        + cip_service_water_eur
        + cip_downtime_eur
        + antiscalant_eur
        + membrane_replacement_eur
    )

    return {
        "cip_per_year": round(cip_per_year, 3),
        "membrane_lifetime_years": round(adjusted_lifetime_years, 3),
        "cip_chemicals_eur": round(cip_chemicals_eur, 2),
        "cip_service_water_eur": round(cip_service_water_eur, 2),
        "cip_downtime_eur": round(cip_downtime_eur, 2),
        "antiscalant_eur": round(antiscalant_eur, 2),
        "membrane_replacement_eur": round(membrane_replacement_eur, 2),
        "total_opex_eur": round(total_opex_eur, 2),
    }


def opex_breakdown_summary(opex_dict: dict) -> None:
    """
    Print a readable annual OPEX breakdown with percentages.
    """
    components = [
        ("CIP chemicals", "cip_chemicals_eur"),
        ("CIP service water", "cip_service_water_eur"),
        ("CIP downtime", "cip_downtime_eur"),
        ("Antiscalant", "antiscalant_eur"),
        ("Membrane replacement", "membrane_replacement_eur"),
    ]
    total = opex_dict["total_opex_eur"]

    print("Annual OPEX breakdown")
    print("-" * 58)
    print(f"{'Component':<28} {'EUR/year':>14} {'Share':>10}")
    print("-" * 58)
    for label, key in components:
        value = opex_dict[key]
        share = (value / total * 100) if total else 0.0
        print(f"{label:<28} {value:>14,.2f} {share:>9.1f}%")
    print("-" * 58)
    print(f"{'Total OPEX':<28} {total:>14,.2f} {100:>9.1f}%")
    print()
    print(f"CIP/year: {opex_dict['cip_per_year']:.3f}")
    print(
        "Adjusted membrane lifetime: "
        f"{opex_dict['membrane_lifetime_years']:.3f} years"
    )
