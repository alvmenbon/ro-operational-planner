from core.opex_estimator import estimate_annual_opex
from core.seasonal_integrator import generate_operational_calendar
from outputs.operational_report import (
    plot_opex_comparison,
    plot_operational_trends,
    plot_seasonal_risk_calendar,
)


LATITUDE = 36.0
LONGITUDE = 14.0
LOCATION_NAME = "Mediterranean test case (36N, 14E)"
FLUX_LMH = 12.0
RECOVERY = 0.45
PH = 7.8
START_YEAR = 2010
END_YEAR = 2020
PLANT_CAPACITY_M3_PER_DAY = 50000
TOTAL_MEMBRANE_ELEMENTS = 1000


def generate_calendar_for_sdi(sdi: float):
    return generate_operational_calendar(
        latitude=LATITUDE,
        longitude=LONGITUDE,
        flux_lmh=FLUX_LMH,
        sdi=sdi,
        recovery=RECOVERY,
        pH=PH,
        start_year=START_YEAR,
        end_year=END_YEAR,
    )


def main() -> None:
    standard_calendar = generate_calendar_for_sdi(3.0)

    risk_path = plot_seasonal_risk_calendar(
        calendar_df=standard_calendar,
        location_name=LOCATION_NAME,
    )
    trends_path = plot_operational_trends(
        calendar_df=standard_calendar,
        location_name=LOCATION_NAME,
    )

    scenarios_results = {}
    for label, sdi in [
        ("A - SDI 2.0", 2.0),
        ("B - SDI 3.0", 3.0),
        ("C - SDI 4.0", 4.0),
    ]:
        calendar = standard_calendar if sdi == 3.0 else generate_calendar_for_sdi(sdi)
        scenarios_results[label] = estimate_annual_opex(
            calendar_df=calendar,
            plant_capacity_m3_per_day=PLANT_CAPACITY_M3_PER_DAY,
            total_membrane_elements=TOTAL_MEMBRANE_ELEMENTS,
        )

    opex_path = plot_opex_comparison(
        scenarios_results=scenarios_results,
        plant_capacity=PLANT_CAPACITY_M3_PER_DAY,
        location_name=LOCATION_NAME,
    )

    print("Visualization files generated:")
    print(risk_path)
    print(trends_path)
    print(opex_path)


if __name__ == "__main__":
    main()
