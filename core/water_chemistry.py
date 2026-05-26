"""
water_chemistry.py

Reconstruye el perfil iónico completo del agua de mar
a partir de la salinidad (PSU) y temperatura (°C).

Base científica: Principio de Forchhammer - la composición
iónica relativa del agua de mar oceánica es constante.
Referencia: Millero et al. (2008), Deep-Sea Research.

Limitaciones:
- Válido para agua de mar oceánica y mares semi-cerrados
- Menor precisión en zonas costeras con aporte fluvial
- No aplicable a aguas salobres o continentales
"""


# --- Composición iónica estándar a 35 PSU ---
# Fracción másica de cada ion respecto a la salinidad total
# Fuente: Millero et al. (2008), composición estándar IAPSO

IONIC_FRACTIONS = {
    "Cl":   0.5516,
    "Na":   0.3061,
    "SO4":  0.0765,
    "Mg":   0.0368,
    "Ca":   0.0116,
    "K":    0.0110,
    "HCO3": 0.0041,
    "Sr":   0.0004,
    "Ba":   0.0000015,
}


def salinity_to_ionic_profile(
    salinity_psu: float,
    temperature_c: float
) -> dict:
    """
    Reconstruye el perfil iónico completo desde salinidad y temperatura.

    Parámetros:
        salinity_psu:  salinidad en PSU (g/kg)
        temperature_c: temperatura en °C

    Retorna:
        dict con concentraciones iónicas en mg/L

    Nota sobre unidades:
        PSU es g de sal por kg de agua de mar.
        Para convertir a mg/L necesitamos la densidad del agua de mar,
        que depende de salinidad y temperatura.
    """
    # Densidad del agua de mar (kg/m³) - aproximación de UNESCO
    density = seawater_density(salinity_psu, temperature_c)

    # Salinidad en g/L (g/kg × kg/L)
    salinity_g_per_L = salinity_psu * (density / 1000)

    # Perfil iónico en mg/L
    profile = {
        ion: fraction * salinity_g_per_L * 1000
        for ion, fraction in IONIC_FRACTIONS.items()
    }

    # SiO2 no sigue el principio de Forchhammer
    # Valor típico para agua de mar oceánica: 1-15 mg/L
    # Usamos valor conservador por defecto, ajustable por el usuario
    profile["SiO2"] = _silica_estimate(temperature_c)

    return {ion: round(conc, 4) for ion, conc in profile.items()}


def seawater_density(salinity_psu: float, temperature_c: float) -> float:
    """
    Calcula la densidad del agua de mar en kg/m³.

    Aproximación lineal válida para:
        Salinidad: 30-45 PSU
        Temperatura: 5-35°C

    Referencia: UNESCO (1983), simplificada para uso en ingeniería.
    """
    rho_fresh = 999.842 - 0.006 * temperature_c ** 2
    rho_seawater = rho_fresh + 0.8 * salinity_psu
    return round(rho_seawater, 2)


def _silica_estimate(temperature_c: float) -> float:
    """
    Estimación de SiO2 en agua de mar oceánica.

    La sílice no sigue el principio de Forchhammer porque
    tiene ciclos biogeoquímicos propios (diatomeas, etc.).
    Rango oceánico típico: 1-15 mg/L.
    Usamos 8 mg/L como valor central conservador.

    El usuario debe ajustar este valor si tiene datos reales.
    """
    # Ligera variación con temperatura (aguas frías tienden
    # a tener más sílice por menor actividad biológica)
    base = 8.0
    correction = -0.1 * (temperature_c - 20)
    return round(max(1.0, base + correction), 2)


def ionic_balance_check(profile_mg_L: dict) -> dict:
    """
    Verifica el balance iónico del perfil.

    Un balance iónico correcto tiene diferencia < 5%
    entre suma de cationes y aniones (en meq/L).

    Retorna dict con cationes, aniones y error porcentual.
    """
    # Equivalentes por mol (valencia / peso molecular)
    eq_weights = {
        "Ca":   40.08 / 2,
        "Mg":   24.31 / 2,
        "Na":   22.99 / 1,
        "K":    39.10 / 1,
        "Sr":   87.62 / 2,
        "Ba":  137.33 / 2,
        "Cl":   35.45 / 1,
        "SO4":  96.06 / 2,
        "HCO3": 61.02 / 1,
    }

    cations = ["Ca", "Mg", "Na", "K", "Sr", "Ba"]
    anions  = ["Cl", "SO4", "HCO3"]

    sum_cations = sum(
        profile_mg_L.get(ion, 0) / eq_weights[ion]
        for ion in cations
    )
    sum_anions = sum(
        profile_mg_L.get(ion, 0) / eq_weights[ion]
        for ion in anions
    )

    error_pct = abs(sum_cations - sum_anions) / ((sum_cations + sum_anions) / 2) * 100

    return {
        "cations_meq_L": round(sum_cations, 3),
        "anions_meq_L":  round(sum_anions, 3),
        "error_pct":     round(error_pct, 2),
        "valid":         error_pct < 5.0
    }