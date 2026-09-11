"""Run the end-to-end local ASG Airlines pipeline."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import pandas as pd

from ingest import load_source_workbook
from profile import create_profile
from transform import clean_flights, clean_bookings, clean_payments, create_safe_passengers
from kpis import create_kpi_tables


def save_csv(dataframe: pd.DataFrame, file_path: Path) -> None:
    dataframe.to_csv(file_path, index=False)


def main(input_file: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    source = load_source_workbook(input_file)
    save_csv(create_profile(source), output_dir / "source_data_profile.csv")

    pii_hash_salt = os.getenv("PII_HASH_SALT", "change-this-before-production")
    flights, rejected_flights = clean_flights(source["flights"])
    bookings, rejected_bookings = clean_bookings(source["bookings"], flights["flight_id"], pii_hash_salt)
    payments, rejected_payments = clean_payments(source["payments"], bookings["booking_id"])
    passengers_safe = create_safe_passengers(source["passengers"], pii_hash_salt)

    outputs = {
        "flights_cleaned.csv": flights,
        "bookings_cleaned.csv": bookings,
        "payments_cleaned.csv": payments,
        "passengers_safe.csv": passengers_safe,
        "rejected_flights.csv": rejected_flights,
        "rejected_bookings.csv": rejected_bookings,
        "rejected_payments.csv": rejected_payments,
    }
    outputs.update({f"{name}.csv": frame for name, frame in create_kpi_tables(flights, bookings, payments).items()})
    for file_name, frame in outputs.items():
        save_csv(frame, output_dir / file_name)

    quality_report = pd.DataFrame(
        [
            {"dataset": "flights", "accepted_records": len(flights), "rejected_records": len(rejected_flights)},
            {"dataset": "bookings", "accepted_records": len(bookings), "rejected_records": len(rejected_bookings)},
            {"dataset": "payments", "accepted_records": len(payments), "rejected_records": len(rejected_payments)},
        ]
    )
    save_csv(quality_report, output_dir / "data_quality_report.csv")
    print(f"Pipeline completed. Outputs saved to: {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the ASG Airlines data pipeline.")
    parser.add_argument("--input", required=True, type=Path, help="Path to the source Excel workbook")
    parser.add_argument("--output", default=Path("data/cleaned"), type=Path, help="Directory for cleaned output files")
    args = parser.parse_args()
    main(args.input, args.output)
