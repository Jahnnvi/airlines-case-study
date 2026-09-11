# ASG Airlines Data Engineering Pipeline

This project cleans airline operational, booking, payment, and passenger data and produces Power BI-ready analytical tables.

## Project flow

```text
Source Excel workbook → Python ingestion → validation and cleaning → cleaned CSV tables → Power BI dashboard
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Put the source workbook in `data/raw/` or supply its full path when running the pipeline.
4. Run from the project root:

```bash
python src/main.py --input "data/raw/UseCase - Airlines.xlsx"
```

Cleaned output files are written to `data/cleaned/`.

## Cleaning rules

- Exact duplicate flight rows are removed.
- Flight IDs, route fields, timestamps, and calculated duration are validated.
- Negative/zero duration, invalid timestamp, invalid route, and malformed flight IDs are rejected.
- Booking statuses must be `CONFIRMED`, `CANCELLED`, or `PENDING`.
- Payments must have a valid booking and a positive numeric amount.
- Direct passenger PII is excluded from reporting output. Passenger IDs are salted and hashed.

## Power BI

Load the cleaned CSV files from `data/cleaned/`. Use `flights_cleaned.csv` for operational KPIs, `bookings_cleaned.csv` for booking KPIs, and the route/airline KPI tables for ready-made visuals.

## Important limitation

The source does not include scheduled versus actual flight times. The project therefore reports duration/data-quality anomalies, not actual flight delays.
