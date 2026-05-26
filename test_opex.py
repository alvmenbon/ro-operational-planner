from core.opex_estimator import estimate_annual_opex, opex_breakdown_summary
from core.seasonal_integrator import generate_operational_calendar


LATITUDE = 36.0
LONGITUDE = 14.0
FLUX_LMH = 12.0
RECOVERY = 0.45
PH = 7.8
START_YEAR = 2010
END_YEAR = 2020
PLANT_CAPACITY_M3_PER_DAY = 50000
TOTAL_MEMBRANE_ELEMENTS = 1000


def run_scenario(label: str, sdi: float) -> dict:
    print()
    print(f"Scenario {label}: SDI={sdi}")
    print("=" * 58)

    calendar = generate_operational_calendar(
        latitude=LATITUDE,
        longitude=LONGITUDE,
        flux_lmh=FLUX_LMH,
        sdi=sdi,
        recovery=RECOVERY,
        pH=PH,
        start_year=START_YEAR,
        end_year=END_YEAR,
    )

    opex = estimate_annual_opex(
        calendar_df=calendar,
        plant_capacity_m3_per_day=PLANT_CAPACITY_M3_PER_DAY,
        total_membrane_elements=TOTAL_MEMBRANE_ELEMENTS,
    )
    opex_breakdown_summary(opex)
    return opex


def print_comparison(results: dict) -> None:
    base_total = results["B"]["total_opex_eur"]

    print()
    print("Scenario comparison")
    print("=" * 72)
    print(
        f"{'Scenario':<12} {'SDI':>6} {'CIP/year':>10} "
        f"{'Total OPEX':>16} {'Delta vs B':>16}"
    )
    print("-" * 72)

    for label, sdi in [("A", 2.0), ("B", 3.0), ("C", 4.0)]:
        opex = results[label]
        total = opex["total_opex_eur"]
        delta = total - base_total
        print(
            f"{label:<12} {sdi:>6.1f} {opex['cip_per_year']:>10.3f} "
            f"{total:>16,.2f} {delta:>16,.2f}"
        )


def main() -> None:
    results = {
        "A": run_scenario("A - excellent pretreatment", 2.0),
        "B": run_scenario("B - standard pretreatment", 3.0),
        "C": run_scenario("C - limited pretreatment", 4.0),
    }
    print_comparison(results)


if __name__ == "__main__":
    main()
