"""Read and validate the ASG Airlines source workbook."""

from pathlib import Path
from typing import Union

import pandas as pd


REQUIRED_SHEETS = {
    "flights",
    "bookings",
    "payments",
    "passengers",
}


REQUIRED_COLUMNS = {
    "flights": {
        "flight_id",
        "airline",
        "source",
        "destination",
        "departure_time",
        "arrival_time",
        "duration",
    },
    "bookings": {
        "booking_id",
        "passenger_id",
        "flight_id",
        "booking_date",
        "status",
        "passport_number",
        "seat_number",
        "emergency_contact_name",
        "emergency_contact_phone",
    },
    "payments": {
        "payment_id",
        "booking_id",
        "amount",
        "payment_method",
    },
    "passengers": {
        "passenger_id",
        "first_name",
        "last_name",
        "age",
        "gender",
        "email",
        "phone",
        "aadhaar_id",
        "date_of_birth",
    },
}


def load_source_workbook(
    file_path: Union[str, Path],
) -> dict[str, pd.DataFrame]:
    """Load and validate the required sheets from the source workbook."""

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Source workbook was not found: {file_path}"
        )

    workbook = pd.ExcelFile(file_path)

    missing_sheets = REQUIRED_SHEETS - set(workbook.sheet_names)

    if missing_sheets:
        raise ValueError(
            f"Workbook is missing required sheets: "
            f"{sorted(missing_sheets)}"
        )

    source = {}

    for sheet in REQUIRED_SHEETS:
        dataframe = pd.read_excel(file_path, sheet_name=sheet)

        missing_columns = REQUIRED_COLUMNS[sheet] - set(dataframe.columns)

        if missing_columns:
            raise ValueError(
                f"Sheet '{sheet}' is missing required columns: "
                f"{sorted(missing_columns)}"
            )

        source[sheet] = dataframe

    return source