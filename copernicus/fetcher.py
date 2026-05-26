"""
fetcher.py

Recupera series temporales de temperatura y salinidad
desde Copernicus Marine Service (CMEMS) para unas
coordenadas geográficas dadas.

Dataset: GLOBAL_MULTIYEAR_PHY_001_030
Resolución: mensual
Cobertura: 1993 - presente
"""

import copernicusmarine
import pandas as pd
import os

def _set_copernicus_credentials():
    """
    Configura credenciales de Copernicus desde Streamlit secrets
    o desde variables de entorno. Solo necesario en despliegue cloud.
    """
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and "COPERNICUSMARINE_SERVICE_USERNAME" in st.secrets:
            os.environ["COPERNICUSMARINE_SERVICE_USERNAME"] = st.secrets["COPERNICUSMARINE_SERVICE_USERNAME"]
            os.environ["COPERNICUSMARINE_SERVICE_PASSWORD"] = st.secrets["COPERNICUSMARINE_SERVICE_PASSWORD"]
    except Exception:
        pass  # En local las credenciales vienen del archivo .copernicusmarine-credentials

DATASET_ID = "cmems_mod_glo_phy_my_0.083deg_P1M-m"

VARIABLES = ["thetao", "so"]  # temperatura y salinidad


def fetch_temperature_salinity(
    latitude: float,
    longitude: float,
    start_year: int = 2010,
    end_year: int = 2020,
    depth_m: float = 0.5
) -> pd.DataFrame:
    """
    Recupera temperatura y salinidad mensual para una ubicación.

    Parámetros:
        latitude:   latitud en grados decimales (+N, -S)
        longitude:  longitud en grados decimales (+E, -W)
        start_year: año de inicio de la serie histórica
        end_year:   año final de la serie histórica
        depth_m:    profundidad en metros (0.5 = superficie)

    Retorna:
        DataFrame con columnas: date, temperature_c, salinity_psu
    """
    start_date = f"{start_year}-01-01T00:00:00"
    end_date   = f"{end_year}-12-31T23:59:59"

    _set_copernicus_credentials()
    
    print(f"Conectando con CMEMS para ({latitude}, {longitude})...")

    ds = copernicusmarine.open_dataset(
        dataset_id=DATASET_ID,
        variables=VARIABLES,
        minimum_latitude=latitude  - 0.1,
        maximum_latitude=latitude  + 0.1,
        minimum_longitude=longitude - 0.1,
        maximum_longitude=longitude + 0.1,
        start_datetime=start_date,
        end_datetime=end_date,
        minimum_depth=depth_m,
        maximum_depth=depth_m,
    )

    # Seleccionar el punto más cercano a las coordenadas dadas
    ds_point = ds.sel(
        latitude=latitude,
        longitude=longitude,
        depth=depth_m,
        method="nearest"
    )

    # Convertir a DataFrame
    df = ds_point[VARIABLES].to_dataframe().reset_index()

    # Limpiar y renombrar
    df = df[["time", "thetao", "so"]].dropna()
    df = df.rename(columns={
        "time":   "date",
        "thetao": "temperature_c",
        "so":     "salinity_psu"
    })

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    print(f"Datos recuperados: {len(df)} meses ({start_year}-{end_year})")

    return df


def monthly_climatology(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula la climatología mensual (promedio histórico por mes).

    Retorna DataFrame con 12 filas (enero a diciembre)
    con temperatura y salinidad promedio histórica.
    """
    df["month"] = df["date"].dt.month

    climatology = df.groupby("month").agg(
        temperature_mean=("temperature_c", "mean"),
        temperature_min=("temperature_c", "min"),
        temperature_max=("temperature_c", "max"),
        salinity_mean=("salinity_psu", "mean"),
        salinity_min=("salinity_psu", "min"),
        salinity_max=("salinity_psu", "max"),
    ).reset_index()

    return climatology.round(3)