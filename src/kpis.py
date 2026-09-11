"""KPI tables for Power BI."""

import pandas as pd


def create_kpi_tables(flights: pd.DataFrame, bookings: pd.DataFrame, payments: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return aggregation-ready KPI tables."""
    route_performance = (
        flights.groupby(["route", "source", "destination"], dropna=False)
        .agg(flight_count=("flight_instance_key", "nunique"), average_duration_minutes=("duration_minutes", "mean"))
        .reset_index()
    )
    airline_distribution = (
        flights.groupby("airline", dropna=False)
        .agg(flight_count=("flight_instance_key", "nunique"), average_duration_minutes=("duration_minutes", "mean"))
        .reset_index()
    )
    booking_status = bookings.groupby("status").agg(booking_count=("booking_id", "nunique")).reset_index()
    overview = pd.DataFrame(
        {
            "metric": ["Valid flight instances", "Average flight duration (minutes)", "Valid bookings", "Confirmed bookings", "Cancellation rate", "Valid payments", "Payment amount"],
            "value": [
                flights["flight_instance_key"].nunique(),
                flights["duration_minutes"].mean(),
                bookings["booking_id"].nunique(),
                (bookings["status"] == "CONFIRMED").sum(),
                (bookings["status"] == "CANCELLED").mean() if len(bookings) else pd.NA,
                payments["payment_id"].nunique(),
                payments["amount"].sum(),
            ],
        }
    )
    return {"route_performance": route_performance, "airline_distribution": airline_distribution, "booking_status": booking_status, "overview_kpis": overview}
