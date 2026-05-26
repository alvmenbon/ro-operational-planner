"""
scaling_indices.py

Calcula índices de saturación de compuestos precipitantes
en agua de mar a lo largo del tren RO.

Inputs: perfil iónico en mg/L, temperatura en °C, recovery en %
Outputs: índices de saturación por compuesto
"""

import numpy as np


# --- Constantes ---

MW = {
    "Ca":   40.08,
    "Mg":   24.31,
    "Na":   22.99,
    "K":    39.10,
    "Sr":   87.62,
    "Ba":  137.33,
    "Cl":   35.45,
    "SO4":  96.06,
    "HCO3": 61.02,
    "CO3":  60.01,
    "SiO2": 60.08,
}


def mg_to_mol(concentration_mg_L: dict) -> dict:
    """
    Convierte concentraciones de mg/L a mol/L.
    """
    return {
        ion: conc / 1000 / MW[ion]
        for ion, conc in concentration_mg_L.items()
    }


def concentrate(feed_mg_L: dict, recovery: float) -> dict:
    """
    Calcula la concentración del concentrado dado el feed y la recovery.

    Recovery en tanto por uno (ej: 0.45 para 45%).
    Factor de concentración = 1 / (1 - recovery)
    """
    if not 0 <= recovery < 1:
        raise ValueError("Recovery debe estar entre 0 y 1")

    cf = 1 / (1 - recovery)

    return {
        ion: conc * cf
        for ion, conc in feed_mg_L.items()
    }


def langelier_saturation_index(profile_mg_L, temperature_c, pH):

    T = temperature_c

    # TDS aproximado
    TDS = sum(profile_mg_L.values())

    # Ca como CaCO3
    Ca = profile_mg_L["Ca"] * (100.09 / 40.08)

    # Alcalinidad como CaCO3 (HCO3 dominante en pH ~7-8)
    Alk = profile_mg_L["HCO3"] * (50.0 / 61.02)

    A = (np.log10(TDS) - 1) / 10
    B = -13.12 * np.log10(T + 273.15) + 34.55
    C = np.log10(Ca) - 0.4
    D = np.log10(Alk)

    pHs = (9.3 + A + B) - (C + D)

    return round(pH - pHs, 3)


def saturation_ratio_CaSO4(profile_mg_L: dict) -> float:
    """
    Ratio de saturación para sulfato de calcio (CaSO4).

    Ksp CaSO4 = 4.93e-5 mol²/L² a 25°C

    SR > 1: riesgo de precipitación
    SR < 1: sin riesgo
    """
    mol = mg_to_mol({k: profile_mg_L[k] for k in ["Ca", "SO4"]})
    gamma_Ca = 0.2
    gamma_SO4 = 0.1
    Ksp = 4.93e-5
    IP = (mol["Ca"] * gamma_Ca) * (mol["SO4"]*gamma_SO4)
    return round(IP / Ksp, 3)


def saturation_ratio_BaSO4(profile_mg_L: dict) -> float:
    """
    Ratio de saturación para sulfato de bario (BaSO4).

    Ksp BaSO4 = 1.1e-10 mol²/L²

    Muy poco soluble: SR > 1 con concentraciones muy bajas de Ba.
    """
    mol = mg_to_mol({k: profile_mg_L[k] for k in ["Ba", "SO4"]})
    gamma_Ba = 0.2
    gamma_SO4 = 0.1
    Ksp = 1.1e-10
    IP = (mol["Ba"] * gamma_Ba) * (mol["SO4"] * gamma_SO4)
    return round(IP / Ksp, 3)


def saturation_ratio_SrSO4(profile_mg_L: dict) -> float:
    """
    Ratio de saturación para sulfato de estroncio (SrSO4).

    Ksp SrSO4 = 3.44e-7 mol²/L²
    """
    mol = mg_to_mol({k: profile_mg_L[k] for k in ["Sr", "SO4"]})
    gamma_Sr = 0.2
    gamma_SO4 = 0.1
    Ksp = 3.44e-7
    IP = (mol["Sr"] * gamma_Sr) * (mol["SO4"] * gamma_SO4)
    return round(IP / Ksp, 3)


def silica_saturation(profile_mg_L: dict, temperature_c: float) -> float:
    """
    Ratio de saturación para sílice (SiO2).

    Solubilidad de sílice amorfa a 25°C: ~120 mg/L
    Aumenta con temperatura.

    SR > 1: riesgo de fouling por sílice
    """
    solubility = 120 * (1 + 0.013 * (temperature_c - 25))
    SR = profile_mg_L.get("SiO2", 0) / solubility
    return round(SR, 3)


def calculate_all_indices(
    feed_mg_L: dict,
    recovery: float,
    temperature_c: float,
    pH: float = 7.5
) -> dict:
    """
    Calcula todos los índices de saturación para el concentrado.

    Parámetros:
        feed_mg_L:     perfil iónico del agua de alimentación en mg/L
        recovery:      recovery en tanto por uno (ej: 0.45)
        temperature_c: temperatura en °C
        pH:            pH del agua (por defecto 7.5)

    Retorna:
        dict con todos los índices y el factor de concentración
    """
    concentrate_mg_L = concentrate(feed_mg_L, recovery)
    cf = 1 / (1 - recovery)

    return {
        "recovery_pct":     round(recovery * 100, 1),
        "concentration_factor": round(cf, 3),
        "LSI_CaCO3":        langelier_saturation_index(concentrate_mg_L, temperature_c, pH),
        "SR_CaSO4":         saturation_ratio_CaSO4(concentrate_mg_L),
        "SR_BaSO4":         saturation_ratio_BaSO4(concentrate_mg_L),
        "SR_SrSO4":         saturation_ratio_SrSO4(concentrate_mg_L),
        "SR_SiO2":          silica_saturation(concentrate_mg_L, temperature_c),
    }

def scaling_profile_along_train(
    feed_mg_L: dict,
    total_recovery: float,
    temperature_c: float,
    pH: float = 7.5,
    n_elements: int = 7
) -> list[dict]:
    """
    Calcula los índices de saturación en cada elemento del tren RO.

    Combina ro_concentration y scaling_indices para dar
    el perfil completo de riesgo a lo largo del tren.

    Retorna lista de dicts, uno por elemento, con:
        - element
        - recovery_cumulative
        - CF
        - índices de saturación en ese punto
    """
    from core.ro_concentration import concentration_profile

    train_profile = concentration_profile(feed_mg_L, total_recovery, n_elements)

    results = []
    for point in train_profile:
        indices = calculate_all_indices(
            feed_mg_L=point["profile"],
            recovery=0.0,          # ya está concentrado, CF=1 aquí
            temperature_c=temperature_c,
            pH=pH
        )

        results.append({
            "element":             point["element"],
            "recovery_cumulative": point["recovery_cumulative"],
            "CF":                  point["CF"],
            "LSI_CaCO3":           indices["LSI_CaCO3"],
            "SR_CaSO4":            indices["SR_CaSO4"],
            "SR_BaSO4":            indices["SR_BaSO4"],
            "SR_SrSO4":            indices["SR_SrSO4"],
            "SR_SiO2":             indices["SR_SiO2"],
        })

    return results


def print_scaling_profile(profile: list[dict]) -> None:
    """
    Imprime el perfil de riesgo de scaling por elemento.
    Marca con ⚠️ los índices que superan el umbral de riesgo.
    """
    print(f"{'Elem':>4} {'CF':>6} {'LSI':>7} {'CaSO4':>7} {'BaSO4':>7} {'SrSO4':>7} {'SiO2':>7}")
    print("-" * 55)

    for p in profile:
        lsi_flag   = "⚠" if p["LSI_CaCO3"] > 0   else " "
        caso4_flag = "⚠" if p["SR_CaSO4"]  > 1   else " "
        baso4_flag = "⚠" if p["SR_BaSO4"]  > 1   else " "
        srso4_flag = "⚠" if p["SR_SrSO4"]  > 1   else " "
        sio2_flag  = "⚠" if p["SR_SiO2"]   > 1   else " "

        print(
            f"{p['element']:>4} "
            f"{p['CF']:>6.3f} "
            f"{p['LSI_CaCO3']:>6.3f}{lsi_flag} "
            f"{p['SR_CaSO4']:>6.3f}{caso4_flag} "
            f"{p['SR_BaSO4']:>6.3f}{baso4_flag} "
            f"{p['SR_SrSO4']:>6.3f}{srso4_flag} "
            f"{p['SR_SiO2']:>6.3f}{sio2_flag}"
        )