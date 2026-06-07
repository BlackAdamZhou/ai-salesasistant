import pandas as pd
import pytest

from app.column_mapper import map_columns, normalise_header


def test_map_columns_handles_actual_pos_headers():
    df = pd.DataFrame(
        columns=[
            "营业日",
            "区域分组",
            "门店名称",
            "商品名称",
            "商品销售数量(销售)",
            "商品销售金额(销售)",
        ]
    )

    mapped = map_columns(df)

    assert {
        "region",
        "date",
        "store_name",
        "product_name",
        "quantity_sold",
        "sales_amount",
    } <= set(mapped.columns)


def test_map_columns_reports_missing_required_columns():
    df = pd.DataFrame(columns=["日期", "门店名称"])

    with pytest.raises(ValueError) as exc:
        map_columns(df)

    assert "Missing required columns" in str(exc.value)


def test_normalise_header_handles_real_pos_punctuation():
    assert normalise_header(" 商品销售金额（销售）\n") == "商品销售金额(销售)"
    assert normalise_header("销售金额：小计") == "销售金额:小计"
