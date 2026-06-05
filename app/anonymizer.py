from __future__ import annotations

import pandas as pd


def anonymise_product_names(
    df: pd.DataFrame,
    source_column: str = "product_name",
    target_column: str = "product_code",
    prefix: str = "Product",
) -> tuple[pd.DataFrame, dict[str, str]]:
    if source_column not in df.columns:
        raise ValueError(f"Missing source column for anonymisation: {source_column}")

    working = df.copy()
    products = sorted(working[source_column].dropna().astype(str).unique())
    mapping = {
        product_name: f"{prefix}_{index:03d}"
        for index, product_name in enumerate(products, start=1)
    }
    working[target_column] = working[source_column].astype(str).map(mapping)
    return working, mapping

