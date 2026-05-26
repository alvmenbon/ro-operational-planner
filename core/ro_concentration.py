"""
ro_concentration.py

Modela la evolución de la concentración iónica a lo largo
del tren de membranas RO elemento a elemento.

Inputs: perfil iónico del feed, recovery total, configuración del tren
Outputs: perfil de concentración por posición en el tren
"""

import numpy as np


def recovery_per_element(total_recovery: float, n_elements: int) -> float:
    """
    Calcula la recovery local por elemento asumiendo
    distribución uniforme de flux a lo largo del vessel.

    Parámetros:
        total_recovery: recovery total del vessel (tanto por uno)
        n_elements:     número de elementos en serie por vessel

    Retorna:
        recovery local por elemento (tanto por uno)
    """
    return 1 - (1 - total_recovery) ** (1 / n_elements)


def concentration_profile(
    feed_mg_L: dict,
    total_recovery: float,
    n_elements: int = 7
) -> list[dict]:
    """
    Calcula el perfil de concentración iónica a lo largo del tren.

    Retorna una lista de dicts, uno por elemento, con:
        - element:    número de elemento (1 a n)
        - recovery_cumulative: recovery acumulada hasta ese punto
        - CF:         factor de concentración acumulado
        - profile:    perfil iónico en mg/L en ese punto
    """
    r_elem = recovery_per_element(total_recovery, n_elements)

    profile = []
    cumulative_permeate_fraction = 0

    for k in range(1, n_elements + 1):
        # Fracción de permeado acumulada hasta el elemento k
        cumulative_permeate_fraction = 1 - (1 - r_elem) ** k

        # Factor de concentración en ese punto
        CF = 1 / (1 - cumulative_permeate_fraction)

        # Perfil iónico concentrado en ese punto
        concentrated = {
            ion: conc * CF
            for ion, conc in feed_mg_L.items()
        }

        profile.append({
            "element":              k,
            "recovery_cumulative":  round(cumulative_permeate_fraction * 100, 2),
            "CF":                   round(CF, 3),
            "profile":              concentrated
        })

    return profile


def max_concentration_point(profile: list[dict]) -> dict:
    """
    Devuelve el punto de máxima concentración del tren.
    Siempre es el último elemento, pero lo hacemos explícito
    para que el código sea legible.
    """
    return profile[-1]


def concentration_profile_summary(profile: list[dict]) -> None:
    """
    Imprime un resumen del perfil de concentración por elemento.
    """
    print(f"{'Elem':>4} {'Rec.Acum%':>10} {'CF':>6}  {'Ca':>8} {'SO4':>8} {'Ba':>8}")
    print("-" * 55)
    for point in profile:
        p = point["profile"]
        print(
            f"{point['element']:>4} "
            f"{point['recovery_cumulative']:>10.1f} "
            f"{point['CF']:>6.3f}  "
            f"{p.get('Ca', 0):>8.1f} "
            f"{p.get('SO4', 0):>8.1f} "
            f"{p.get('Ba', 0):>8.4f}"
        )