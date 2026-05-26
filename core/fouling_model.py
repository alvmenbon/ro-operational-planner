"""
fouling_model.py

Motor físico de ensuciamiento de membranas RO basado en
el modelo de resistencias en serie (Darcy).

El fouling aumenta la resistencia hidráulica de la membrana
con el tiempo, lo que se traduce en un aumento del diferencial
de presión normalizado (NDP) para mantener el mismo flux.

Referencias:
    - Darcy, H. (1856). Les fontaines publiques de la ville de Dijon.
    - Field, R.W. et al. (1995). Critical flux concept for microfiltration fouling.
    - ASTM D4194 - Standard Operating Procedures for RO systems.
"""

import numpy as np


# --- Parámetros por defecto de membrana SW (DuPont SW30HR) ---

DEFAULT_MEMBRANE = {
    "A":    3.5e-12,
    "kf":   2.5e12,   # coeficiente de fouling (m⁻¹/day^n)
    "n":    0.7,      # exponente de fouling
}


def osmotic_pressure(tds_mg_L: float, temperature_c: float) -> float:
    """
    Calcula la presión osmótica del agua en Pa.

    Aproximación de Van't Hoff para agua de mar.

    Parámetros:
        tds_mg_L:      TDS en mg/L
        temperature_c: temperatura en °C

    Retorna:
        presión osmótica en Pa
    """
    T = temperature_c + 273.15
    # Coeficiente empírico para agua de mar: ~8 Pa por mg/L de TDS a 25°C
    pi = 8.0 * tds_mg_L * (T / 298.15)
    return pi


def flux_to_velocity(flux_lmh: float) -> float:
    """
    Convierte flux de membrana de L/m²/h a m/s.
    """
    return flux_lmh / 3.6e6


def fouling_resistance(
    time_days: float,
    flux_lmh: float,
    sdi: float,
    temperature_c: float,
    membrane: dict = None
) -> float:
    """
    Calcula la resistencia de fouling acumulada (m⁻¹).

    Modelo de ley potencial, más representativo de RO real:
        R_f = kf × SDI_factor × flux_factor × t^n

    El NDP en plantas RO reales sigue una subida gradual continua,
    no un equilibrio exponencial. La ley potencial captura mejor
    ese comportamiento (Field et al., datos SWRO industriales).

    n=0.7: fouling con compactación progresiva del cake
    n=1.0: crecimiento lineal
    n=0.5: difusión limitada
    """
    if membrane is None:
        membrane = DEFAULT_MEMBRANE

    if time_days <= 0:
        return 0.0

    kf = membrane["kf"]
    n  = membrane["n"]

    # Factor SDI: normalizado sobre SDI=3 como referencia
    sdi_factor = (sdi / 3.0) ** 1.5

    # Factor flux: normalizado sobre 12 LMH como referencia
    flux_factor = (flux_lmh / 12.0) ** 1.2

    # Factor temperatura: fouling biológico aumenta con temperatura
    temp_factor = np.exp(0.02 * (temperature_c - 20))

    R_fouling = kf * sdi_factor * flux_factor * temp_factor * (time_days ** n)

    return R_fouling

def normalized_pressure_drop(
    time_days: float,
    flux_lmh: float,
    sdi: float,
    tds_mg_L: float,
    temperature_c: float,
    membrane: dict = None
) -> float:
    """
    Calcula el diferencial de presión normalizado (NDP ratio).

    NDP ratio = NDP(t) / NDP(t=0)

    Un NDP ratio de 1.15 (15% de aumento) es el umbral
    estándar de la industria para programar una limpieza CIP.

    Parámetros:
        time_days:     días desde la última limpieza
        flux_lmh:      flux en L/m²/h
        sdi:           SDI del agua de alimentación
        tds_mg_L:      TDS en mg/L
        temperature_c: temperatura en °C
        membrane:      parámetros de membrana

    Retorna:
        NDP ratio (adimensional, 1.0 = membrana limpia)
    """
    if membrane is None:
        membrane = DEFAULT_MEMBRANE

    Jw = flux_to_velocity(flux_lmh)
    mu = 1e-3 * np.exp(-0.025 * (temperature_c - 20))
    pi = osmotic_pressure(tds_mg_L, temperature_c)

    # Resistencia intrínseca de la membrana
    A = membrane["A"]
    R_membrane = 1 / (A * mu) if A * mu > 0 else 1e12

    # Resistencia de fouling acumulada
    R_fouling = fouling_resistance(time_days, flux_lmh, sdi, temperature_c, membrane)

    # NDP ratio correcto para RO
    # La presión adicional por fouling normalizada sobre NDP limpio
    ndp_ratio = 1 + A * mu * R_fouling

    return round(ndp_ratio, 4)


def days_to_cip_threshold(
    flux_lmh: float,
    sdi: float,
    tds_mg_L: float,
    temperature_c: float,
    threshold: float = 1.15,
    max_days: int = 365,
    membrane: dict = None
) -> int:
    """
    Calcula los días hasta alcanzar el umbral de limpieza CIP.

    Itera día a día hasta que el NDP ratio supera el threshold.

    Parámetros:
        flux_lmh:      flux en L/m²/h
        sdi:           SDI del agua de alimentación
        tds_mg_L:      TDS en mg/L
        temperature_c: temperatura en °C
        threshold:     NDP ratio que dispara la limpieza (default 1.15)
        max_days:      límite de simulación en días
        membrane:      parámetros de membrana

    Retorna:
        días hasta la limpieza CIP (int)
    """
    for day in range(1, max_days + 1):
        ndp = normalized_pressure_drop(
            time_days=day,
            flux_lmh=flux_lmh,
            sdi=sdi,
            tds_mg_L=tds_mg_L,
            temperature_c=temperature_c,
            membrane=membrane
        )
        if ndp >= threshold:
            return day

    return max_days