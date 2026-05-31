import os

import matplotlib.pyplot as plt
import streamlit as st

from core.opex_estimator import estimate_annual_opex
from core.seasonal_integrator import generate_operational_calendar
from outputs.operational_report import (
    plot_opex_comparison,
    plot_operational_trends,
    plot_seasonal_risk_calendar,
)


st.set_page_config(
    page_title="RO Operational Planner",
    layout="wide",
)

try:
    if hasattr(st, "secrets") and "COPERNICUSMARINE_SERVICE_USERNAME" in st.secrets:
        os.environ["COPERNICUSMARINE_SERVICE_USERNAME"] = st.secrets[
            "COPERNICUSMARINE_SERVICE_USERNAME"
        ]
        os.environ["COPERNICUSMARINE_SERVICE_PASSWORD"] = st.secrets[
            "COPERNICUSMARINE_SERVICE_PASSWORD"
        ]
except Exception:
    pass


def format_eur(value: float) -> str:
    return f"{value:,.0f} EUR"


def run_calendar(latitude, longitude, flux_lmh, sdi, recovery, pH):
    return generate_operational_calendar(
        latitude=latitude,
        longitude=longitude,
        flux_lmh=flux_lmh,
        sdi=sdi,
        recovery=recovery,
        pH=pH,
        start_year=2010,
        end_year=2020,
    )


st.title("RO Operational Planner")
st.caption(
    "Seasonal scaling, fouling and OPEX analysis for coastal RO desalination."
)

with st.sidebar:
    st.header("Design Inputs")
    latitude = st.slider("Latitude", -90.0, 90.0, 36.0, step=0.1)
    longitude = st.slider("Longitude", -180.0, 180.0, 14.0, step=0.1)
    flux_lmh = st.slider("Design flux LMH", 10.0, 18.0, 12.0, step=0.5)
    sdi = st.slider("SDI target", 1.5, 5.0, 3.0, step=0.1)
    recovery_pct = st.slider("Recovery", 30, 60, 45, step=1)
    pH = st.slider("Feed pH", 6.5, 8.5, 7.8, step=0.1)
    plant_capacity = st.number_input(
        "Plant capacity m3/day",
        min_value=1,
        value=50000,
        step=1000,
    )
    total_membrane_elements = st.number_input(
        "Total membrane elements",
        min_value=1,
        value=1000,
        step=100,
    )
    run_analysis = st.button("Run Analysis", type="primary", use_container_width=True)

    st.divider()
    st.header("About")
    st.markdown(
        "Integrated seasonal RO planning tool combining Copernicus Marine data, "
        "scaling risk, fouling behavior and membrane OPEX."
    )
    st.markdown("Built by **Álvaro Mendoza**, Process Engineer")
    st.markdown(
        "[![LinkedIn](https://img.shields.io/badge/LinkedIn-Alvaro%20Mendoza-0A66C2?logo=linkedin&logoColor=white)]"
        "(https://www.linkedin.com/in/alvaro-mendoza-bonilla)"
    )
    st.markdown(
        "[![GitHub](https://img.shields.io/badge/GitHub-ro--operational--planner-181717?logo=github&logoColor=white)]"
        "(https://github.com/alvmenbon/ro-operational-planner)"
    )


if not run_analysis:
    st.info("Set the design inputs in the sidebar and run the analysis.")
    st.stop()


recovery = recovery_pct / 100
location_name = f"{latitude:.1f}N, {longitude:.1f}E"

with st.spinner("Retrieving data and calculating..."):
    calendar = run_calendar(latitude, longitude, flux_lmh, sdi, recovery, pH)
    opex = estimate_annual_opex(
        calendar_df=calendar,
        plant_capacity_m3_per_day=plant_capacity,
        total_membrane_elements=total_membrane_elements,
    )

    scenarios_results = {}
    for label, scenario_sdi in [
        ("A - SDI 2.0", 2.0),
        ("B - SDI 3.0", 3.0),
        ("C - SDI 4.0", 4.0),
    ]:
        scenario_calendar = (
            calendar
            if abs(scenario_sdi - sdi) < 1e-9
            else run_calendar(latitude, longitude, flux_lmh, scenario_sdi, recovery, pH)
        )
        scenarios_results[label] = estimate_annual_opex(
            calendar_df=scenario_calendar,
            plant_capacity_m3_per_day=plant_capacity,
            total_membrane_elements=total_membrane_elements,
        )


critical_row = calendar.loc[calendar["LSI_CaCO3"].idxmax()]
critical_month = int(critical_row["month"])

metric_cols = st.columns(4)
metric_cols[0].metric("Critical month", critical_month)
metric_cols[1].metric("Average CIP/year", f"{opex['cip_per_year']:.2f}")
metric_cols[2].metric("Annual OPEX", format_eur(opex["total_opex_eur"]))
metric_cols[3].metric(
    "Membrane lifetime years",
    f"{opex['membrane_lifetime_years']:.2f}",
)

st.subheader("Seasonal Risk Calendar")
risk_fig = plot_seasonal_risk_calendar(calendar, location_name, return_fig=True)
st.pyplot(risk_fig, clear_figure=False)
plt.close(risk_fig)

st.subheader("Operational Trends")
trends_fig = plot_operational_trends(calendar, location_name, return_fig=True)
st.pyplot(trends_fig, clear_figure=False)
plt.close(trends_fig)

st.subheader("OPEX Comparison")
opex_fig = plot_opex_comparison(
    scenarios_results,
    plant_capacity,
    location_name,
    return_fig=True,
)
st.pyplot(opex_fig, clear_figure=False)
plt.close(opex_fig)

with st.expander("Operational calendar data"):
    st.dataframe(calendar, use_container_width=True)

st.caption(
    "Model limitations: simplified scaling and fouling physics, constant annual SDI, "
    "synthetic operating assumptions, and typical SWRO cost coefficients. Recalibrate "
    "with local feed-water data, plant history and site-specific costs before using "
    "for final design or investment decisions."
)
