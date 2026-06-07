import pandas as pd
import pytest

from app.file_parser import clean_sales_dataframe, read_sales_file


def test_clean_sales_dataframe_drops_stringified_empty_values():
    df = pd.DataFrame(
        {
            "date": ["2026-04-01", "2026-04-02", "2026-04-03"],
            "store_name": ["Store A", None, "nan"],
            "product_name": ["Product A", "Product B", "Product C"],
            "quantity_sold": [1, 2, 3],
            "sales_amount": [10, 20, 30],
        }
    )

    cleaned = clean_sales_dataframe(df)

    assert len(cleaned) == 1
    assert cleaned.iloc[0]["store_name"] == "Store A"


def test_read_sales_file_rejects_xls_without_xlrd_dependency():
    with pytest.raises(ValueError) as exc:
        read_sales_file("sales.xls", b"")

    assert ".xlsx or .csv" in str(exc.value)
