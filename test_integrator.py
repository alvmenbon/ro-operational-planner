from core.seasonal_integrator import generate_operational_calendar


def main() -> None:
    calendar = generate_operational_calendar(
        latitude=36.0,
        longitude=14.0,
        flux_lmh=12.0,
        sdi=3.0,
        recovery=0.45,
        pH=7.8,
        start_year=2010,
        end_year=2020,
    )

    print(calendar.to_string(index=False))


if __name__ == "__main__":
    main()
