"""
seasonal_integrator.py

Integra climatologia mensual, quimica del agua, scaling y fouling
para generar un calendario operacional anual de RO.
"""

import pandas as pd

from copernicus.fetcher import fetch_temperature_salinity, monthly_climatology
from core.fouling_model import days_to_cip_threshold
from core.scaling_indices import calculate_all_indices
from core.water_chemistry import salinity_to_ionic_profile


def generate_operational_calendar(
    latitude: float,
    longitude: float,
    flux_lmh: float,
    sdi: float,
    recovery: float,
    pH: float,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """
    Generate a monthly RO operational calendar from Copernicus climatology.

    Parameters
    ----------
    latitude : float
        Latitude in decimal degrees.
    longitude : float
        Longitude in decimal degrees.
    flux_lmh : float
        Membrane flux in L/m2/h.
    sdi : float
        Feed water silt density index.
    recovery : float
        RO recovery as a fraction, for example 0.45 for 45%.
    pH : float
        Feed water pH used for scaling index calculations.
    start_year : int
        First year of the historical Copernicus time series.
    end_year : int
        Last year of the historical Copernicus time series.

    Returns
    -------
    pandas.DataFrame
        Monthly calendar with temperature, salinity, TDS, scaling indices,
        days to CIP, and estimated CIP events per year.
    """
    print("Fetching monthly temperature and salinity data...")
    monthly_data = fetch_temperature_salinity(
        latitude=latitude,
        longitude=longitude,
        start_year=start_year,
        end_year=end_year,
    )

    print("Calculating monthly climatology...")
    climatology = monthly_climatology(monthly_data)

    rows = []
    for month in range(1, 13):
        print(f"Processing month {month}...")
        month_data = climatology.loc[climatology["month"] == month]
        if month_data.empty:
            raise ValueError(f"No climatology data available for month {month}")

        temperature_c = float(month_data.iloc[0]["temperature_mean"])
        salinity_psu = float(month_data.iloc[0]["salinity_mean"])

        ionic_profile = salinity_to_ionic_profile(
            salinity_psu=salinity_psu,
            temperature_c=temperature_c,
        )
        scaling = calculate_all_indices(
            feed_mg_L=ionic_profile,
            recovery=recovery,
            temperature_c=temperature_c,
            pH=pH,
        )
        tds_mg_L = sum(ionic_profile.values())
        days_to_cip = days_to_cip_threshold(
            flux_lmh=flux_lmh,
            sdi=sdi,
            tds_mg_L=tds_mg_L,
            temperature_c=temperature_c,
        )

        rows.append(
            {
                "month": month,
                "temperature_c": round(temperature_c, 3),
                "salinity_psu": round(salinity_psu, 3),
                "tds_mg_L": round(tds_mg_L, 3),
                "LSI_CaCO3": scaling["LSI_CaCO3"],
                "SR_CaSO4": scaling["SR_CaSO4"],
                "SR_BaSO4": scaling["SR_BaSO4"],
                "SR_SrSO4": scaling["SR_SrSO4"],
                "SR_SiO2": scaling["SR_SiO2"],
                "days_to_cip": days_to_cip,
                "cip_per_year": round(365 / days_to_cip, 3),
            }
        )

    print("Operational calendar generated.")
    return pd.DataFrame(
        rows,
        columns=[
            "month",
            "temperature_c",
            "salinity_psu",
            "tds_mg_L",
            "LSI_CaCO3",
            "SR_CaSO4",
            "SR_BaSO4",
            "SR_SrSO4",
            "SR_SiO2",
            "days_to_cip",
            "cip_per_year",
        ],
    )
