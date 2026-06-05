from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


COLUMN_ALIASES: dict[str, list[str]] = {
    "region": [
        "region",
        "area",
        "district",
        "区域",
        "区域分组",
        "大区",
        "片区",
        "门店区域",
    ],
    "date": [
        "date",
        "sales_date",
        "transaction_date",
        "日期",
        "销售日期",
        "交易日期",
        "时间",
        "销售时间",
        "营业日",
    ],
    "store_name": [
        "store_name",
        "store",
        "shop",
        "branch",
        "门店",
        "店铺",
        "店名",
        "门店名称",
        "店铺名称",
        "分店",
    ],
    "product_name": [
        "product_name",
        "product",
        "sku_name",
        "item_name",
        "商品",
        "商品名称",
        "品名",
        "产品名称",
        "货品名称",
        "SKU名称",
    ],
    "quantity_sold": [
        "quantity_sold",
        "quantity",
        "qty",
        "sold_qty",
        "sales_qty",
        "销量",
        "数量",
        "销售数量",
        "销售件数",
        "实销数量",
        "出库数量",
        "商品销售数量",
        "商品销售数量(销售)",
    ],
    "sales_amount": [
        "sales_amount",
        "amount",
        "revenue",
        "sales",
        "total_amount",
        "销售金额",
        "金额",
        "实收金额",
        "应收金额",
        "成交金额",
        "销售额",
        "小计",
        "商品销售金额",
        "商品销售金额(销售)",
        "商品销售金额(不含券)",
        "商品销售金额(券售价)",
    ],
    "stock_remaining": [
        "stock_remaining",
        "stock",
        "inventory",
        "remaining_stock",
        "库存",
        "剩余库存",
        "当前库存",
        "库存数量",
        "结余库存",
    ],
}

REQUIRED_COLUMNS = {
    "date",
    "store_name",
    "product_name",
    "quantity_sold",
    "sales_amount",
}

SUMMARY_ROW_MARKERS = {"合计", "总计", "小计", "subtotal", "total"}


@dataclass(frozen=True)
class ColumnMappingResult:
    mapped_columns: dict[str, str]
    missing_required_columns: list[str]
    score: int


def normalise_header(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().lower()
    return "".join(text.split())


def _alias_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for internal_name, aliases in COLUMN_ALIASES.items():
        lookup[normalise_header(internal_name)] = internal_name
        for alias in aliases:
            lookup[normalise_header(alias)] = internal_name
    return lookup


ALIAS_LOOKUP = _alias_lookup()


def detect_column_mapping(columns: list[object]) -> ColumnMappingResult:
    mapped_columns: dict[str, str] = {}
    seen_internal: set[str] = set()

    for column in columns:
        normalised = normalise_header(column)
        internal_name = ALIAS_LOOKUP.get(normalised)
        if internal_name and internal_name not in seen_internal:
            mapped_columns[str(column)] = internal_name
            seen_internal.add(internal_name)

    missing = sorted(REQUIRED_COLUMNS - seen_internal)
    return ColumnMappingResult(
        mapped_columns=mapped_columns,
        missing_required_columns=missing,
        score=len(seen_internal),
    )


def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = detect_column_mapping(list(df.columns))
    if result.missing_required_columns:
        available = [str(column) for column in df.columns]
        missing = ", ".join(result.missing_required_columns)
        raise ValueError(
            f"Missing required columns after mapping: {missing}. "
            f"Available columns: {available}"
        )

    return df.rename(columns=result.mapped_columns)
