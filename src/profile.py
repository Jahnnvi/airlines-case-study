"""Reusable data-profiling functions for the source workbook."""

import pandas as pd


def create_profile(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Create one data-quality profile row for every source column."""
    rows = []
    for dataset, dataframe in datasets.items():
        for column in dataframe.columns:
            series = dataframe[column]
            rows.append(
                {
                    "dataset": dataset,
                    "column": column,
                    "row_count": len(dataframe),
                    "data_type": str(series.dtype),
                    "null_count": int(series.isna().sum()),
                    "null_percent": round(float(series.isna().mean() * 100), 2),
                    "distinct_count": int(series.nunique(dropna=True)),
                    "duplicate_row_count": int(dataframe.duplicated().sum()),
                }
            )
    return pd.DataFrame(rows)
