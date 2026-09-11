"""Cleaning and privacy transformations for ASG Airlines source data."""

from __future__ import annotations

import hashlib
import re
from typing import Iterable
import pandas as pd

FLIGHT_ID_PATTERN = re.compile(r"^(AI|6F|SJ|UK)\d{3}$")
VALID_BOOKING_STATUSES = {"CONFIRMED", "CANCELLED", "PENDING"}


def _clean_text(series: pd.Series, uppercase: bool = False) -> pd.Series:
    result = series.astype("string").str.strip()
    result = result.replace({"": pd.NA, "NAN": pd.NA, "NONE": pd.NA, "<NA>": pd.NA})
    return result.str.upper() if uppercase else result


def clean_flights(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create valid and rejected flight-operation records."""
    df = raw.copy().drop_duplicates().reset_index(drop=True)
    df["flight_id"] = _clean_text(df["flight_id"], uppercase=True)
    df["airline"] = _clean_text(df["airline"])
    df["source"] = _clean_text(df["source"], uppercase=True)
    df["destination"] = _clean_text(df["destination"], uppercase=True)
    df["departure_time"] = pd.to_datetime(df["departure_time"], errors="coerce")
    df["arrival_time"] = pd.to_datetime(df["arrival_time"], errors="coerce")

    df["airline"] = df["airline"].mask(df["airline"].str.upper().eq("UNKNOWN"), "Unknown")
    df["airline"] = df["airline"].fillna("Unknown")
    df["duration_minutes"] = (df["arrival_time"] - df["departure_time"]).dt.total_seconds() / 60
    df["is_overnight"] = (
        df["arrival_time"].dt.date > df["departure_time"].dt.date
    
    )
    df["route"] = df["source"].fillna("?") + "-" + df["destination"].fillna("?")
    df["flight_instance_key"] = (
        df["flight_id"].fillna("INVALID")
        + "_"
        + df["departure_time"].dt.strftime("%Y%m%d%H%M%S").fillna("INVALID")
    )

    reasons: list[list[str]] = []
    for row in df.itertuples(index=False):
        row_reasons = []
        if pd.isna(row.flight_id) or not FLIGHT_ID_PATTERN.fullmatch(str(row.flight_id)):
            row_reasons.append("invalid_flight_id")
        if pd.isna(row.source) or pd.isna(row.destination):
            row_reasons.append("missing_route_city")
        elif row.source == row.destination:
            row_reasons.append("same_source_and_destination")
        if pd.isna(row.departure_time) or pd.isna(row.arrival_time):
            row_reasons.append("invalid_timestamp")
        elif pd.isna(row.duration_minutes) or row.duration_minutes <= 0:
            row_reasons.append("invalid_duration")
        reasons.append(row_reasons)

    df["reject_reason"] = [";".join(item) if item else pd.NA for item in reasons]
    df["record_status"] = df["reject_reason"].isna().map({True: "accepted", False: "rejected"})
    df["processed_at"] = pd.Timestamp.now(tz="UTC")
    return df[df["record_status"] == "accepted"].copy(), df[df["record_status"] == "rejected"].copy()


def _hash_identifier(value: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()


def clean_bookings(raw: pd.DataFrame, valid_flight_ids: Iterable[str], salt: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Clean booking records and retain only non-PII operational fields."""
    df = raw.copy().drop_duplicates().reset_index(drop=True)
    df["booking_id"] = _clean_text(df["booking_id"], uppercase=True)
    df["flight_id"] = _clean_text(df["flight_id"], uppercase=True)
    df["passenger_id"] = _clean_text(df["passenger_id"], uppercase=True)
    df["status"] = _clean_text(df["status"], uppercase=True)
    df["booking_date"] = pd.to_datetime(df["booking_date"], errors="coerce")
    df["has_valid_flight"] = df["flight_id"].isin(set(valid_flight_ids))
    df["passenger_key"] = df["passenger_id"].fillna("MISSING").map(lambda value: _hash_identifier(value, salt))

    conditions = [
        df["booking_id"].isna(),
        df["passenger_id"].isna(),
        df["flight_id"].isna() | ~df["has_valid_flight"],
        ~df["status"].isin(VALID_BOOKING_STATUSES),
        df["booking_date"].isna(),
    ]
    labels = ["missing_booking_id", "missing_passenger_id", "invalid_flight_reference", "invalid_status", "invalid_booking_date"]
    df["reject_reason"] = pd.NA
    for condition, label in zip(conditions, labels):
        df.loc[condition, "reject_reason"] = df.loc[condition, "reject_reason"].fillna("").astype(str).str.strip(";") + ";" + label
    df["reject_reason"] = df["reject_reason"].astype("string").str.strip(";").replace("", pd.NA)
    df["record_status"] = df["reject_reason"].isna().map({True: "accepted", False: "rejected"})
    df["processed_at"] = pd.Timestamp.now(tz="UTC")
    safe_columns = ["booking_id", "passenger_key", "flight_id", "booking_date", "status", "record_status", "reject_reason", "processed_at"]
    safe = df[safe_columns].copy()
    return safe[safe["record_status"] == "accepted"].copy(), safe[safe["record_status"] == "rejected"].copy()


def clean_payments(raw: pd.DataFrame, valid_booking_ids: Iterable[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Clean payments and reject missing, non-numeric, or non-positive amounts."""
    df = raw.copy().drop_duplicates().reset_index(drop=True)
    df["payment_id"] = _clean_text(df["payment_id"], uppercase=True)
    df["booking_id"] = _clean_text(df["booking_id"], uppercase=True)
    df["payment_method"] = _clean_text(df["payment_method"], uppercase=True)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["reject_reason"] = pd.NA
    df.loc[df["payment_id"].isna(), "reject_reason"] = "missing_payment_id"
    df.loc[df["booking_id"].isna() | ~df["booking_id"].isin(set(valid_booking_ids)), "reject_reason"] = "invalid_booking_reference"
    df.loc[df["amount"].isna() | (df["amount"] <= 0), "reject_reason"] = "invalid_payment_amount"
    df["record_status"] = df["reject_reason"].isna().map({True: "accepted", False: "rejected"})
    df["processed_at"] = pd.Timestamp.now(tz="UTC")
    return df[df["record_status"] == "accepted"].copy(), df[df["record_status"] == "rejected"].copy()


def create_safe_passengers(raw: pd.DataFrame, salt: str) -> pd.DataFrame:
    """Remove direct PII and create a privacy-safe passenger reference table."""
    df = raw.copy().drop_duplicates(subset=["passenger_id"], keep="first").reset_index(drop=True)
    df["passenger_id"] = _clean_text(df["passenger_id"], uppercase=True)
    df["passenger_key"] = df["passenger_id"].fillna("MISSING").map(lambda value: _hash_identifier(value, salt))
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    df["gender"] = _clean_text(df["gender"], uppercase=True).fillna("Unknown")
    df["date_of_birth"] = pd.to_datetime(df["date_of_birth"], errors="coerce")
    return df[["passenger_key", "age", "gender", "date_of_birth"]].copy()
