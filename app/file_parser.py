from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd

from app.column_mapper import (
    REQUIRED_COLUMNS,
    SUMMARY_ROW_MARKERS,
    detect_column_mapping,
    map_columns,
)


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def read_sales_file(filename: str, content: bytes) -> pd.DataFrame:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported file type. Please upload .xlsx, .xls, or .csv.")

    if extension == ".csv":
        df = _read_csv(content)
    else:
        df = _read_excel(content)

    mapped = map_columns(df)
    return clean_sales_dataframe(mapped)


def _read_csv(content: bytes) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return pd.read_csv(BytesIO(content), encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError(f"Unable to decode CSV file: {last_error}")


def _read_excel(content: bytes) -> pd.DataFrame:
    excel_bytes = BytesIO(content)
    workbook = pd.ExcelFile(excel_bytes)
    best_candidate: tuple[int, str, int] | None = None

    for sheet_name in workbook.sheet_names:
        preview = pd.read_excel(
            BytesIO(content),
            sheet_name=sheet_name,
            header=None,
            nrows=20,
        )
        for row_index in range(len(preview)):
            row_values = preview.iloc[row_index].tolist()
            score = detect_column_mapping(row_values).score
            if best_candidate is None or score > best_candidate[0]:
                best_candidate = (score, sheet_name, row_index)

    if not best_candidate:
        raise ValueError("Unable to inspect Excel workbook.")

    score, sheet_name, header_row = best_candidate
    if score < len(REQUIRED_COLUMNS):
        raise ValueError("Unable to detect a valid header row in the Excel file.")

    return pd.read_excel(BytesIO(content), sheet_name=sheet_name, header=header_row)


def clean_sales_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    working = df.copy()
    keep_columns = [
        "region",
        "date",
        "store_name",
        "product_name",
        "quantity_sold",
        "sales_amount",
        "stock_remaining",
    ]
    working = working[[column for column in keep_columns if column in working.columns]]

    for column in ("region", "store_name", "product_name"):
        if column in working.columns:
            working[column] = working[column].astype(str).str.strip()

    marker_pattern = "|".join(SUMMARY_ROW_MARKERS)
    summary_mask = (
        working["store_name"].str.lower().str.contains(marker_pattern, na=False)
        | working["product_name"].str.lower().str.contains(marker_pattern, na=False)
    )
    working = working.loc[~summary_mask].copy()

    working["date"] = parse_sales_dates(working["date"])
    working["quantity_sold"] = pd.to_numeric(working["quantity_sold"], errors="coerce")
    working["sales_amount"] = pd.to_numeric(working["sales_amount"], errors="coerce")
    if "stock_remaining" in working.columns:
        working["stock_remaining"] = pd.to_numeric(
            working["stock_remaining"], errors="coerce"
        )

    required = ["date", "store_name", "product_name", "quantity_sold", "sales_amount"]
    working = working.dropna(subset=required)
    working = working.loc[
        (working["quantity_sold"] >= 0) & (working["sales_amount"] >= 0)
    ].copy()

    if working.empty:
        raise ValueError("No valid sales rows remain after cleaning.")

    working["date"] = working["date"].dt.normalize()
    return working.reset_index(drop=True)


def parse_sales_dates(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip()
    compact_date_mask = text.str.fullmatch(r"\d{8}(\.0)?")

    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    if compact_date_mask.any():
        compact_values = text.loc[compact_date_mask].str.replace(
            r"\.0$", "", regex=True
        )
        parsed.loc[compact_date_mask] = pd.to_datetime(
            compact_values, format="%Y%m%d", errors="coerce"
        )

    remaining_mask = ~compact_date_mask
    if remaining_mask.any():
        parsed.loc[remaining_mask] = pd.to_datetime(
            series.loc[remaining_mask], errors="coerce"
        )
    return parsed
