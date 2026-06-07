from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd


XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def build_analysis_workbook(
    analysis_summary: dict,
    ai_report: str | None = None,
) -> BytesIO:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        _write_summary_sheet(writer, analysis_summary, ai_report)
        _write_table(
            writer,
            "门店表现",
            analysis_summary.get("store_performance", []),
            [
                "store_name",
                "region",
                "total_sales_amount",
                "total_quantity_sold",
                "transaction_count",
                "sales_days",
                "average_daily_sales",
                "best_sales_date",
                "best_day_sales",
            ],
        )
        _write_table(
            writer,
            "商品销售额",
            analysis_summary.get("top_products", []),
            [
                "product_code",
                "total_sales_amount",
                "total_quantity_sold",
                "sales_frequency",
                "sales_days",
                "covered_store_count",
                "average_sales_amount",
                "average_daily_quantity",
                "sales_velocity",
                "single_store_daily_quantity",
                "average_stock_remaining",
            ],
        )
        _write_table(
            writer,
            "动销速度",
            analysis_summary.get("fast_moving_products", []),
            [
                "product_code",
                "sales_velocity",
                "total_quantity_sold",
                "total_sales_amount",
                "sales_frequency",
                "sales_days",
                "covered_store_count",
                "single_store_daily_quantity",
            ],
        )
        _write_stocking_sheet(writer, analysis_summary)
        _write_table(
            writer,
            "低动销商品",
            _low_moving_rows(analysis_summary),
            [
                "product_code",
                "total_sales_amount",
                "total_quantity_sold",
                "sales_velocity",
                "sales_frequency",
                "sales_days",
                "covered_store_count",
                "single_store_daily_quantity",
                "reason",
            ],
        )
        _write_date_sheet(writer, analysis_summary)
        _write_table(
            writer,
            "区域表现",
            analysis_summary.get("region_performance", []),
            [
                "region",
                "total_sales_amount",
                "total_quantity_sold",
                "store_count",
                "transaction_count",
                "sales_days",
                "average_daily_sales",
            ],
        )

    output.seek(0)
    return output


def _write_summary_sheet(
    writer: pd.ExcelWriter,
    analysis_summary: dict[str, Any],
    ai_report: str | None,
) -> None:
    date_range = analysis_summary.get("date_range", {})
    date_metrics = analysis_summary.get("date_sales_relationship", {})
    rows = [
        {"metric": "row_count", "value": analysis_summary.get("row_count")},
        {"metric": "product_count", "value": analysis_summary.get("product_count")},
        {"metric": "store_count", "value": analysis_summary.get("store_count")},
        {"metric": "start_date", "value": date_range.get("start_date")},
        {"metric": "end_date", "value": date_range.get("end_date")},
        {"metric": "sales_days", "value": date_range.get("sales_days")},
        {
            "metric": "has_stock_column",
            "value": analysis_summary.get("has_stock_column"),
        },
        {"metric": "peak_date", "value": date_metrics.get("peak_date")},
        {
            "metric": "peak_date_sales_amount",
            "value": date_metrics.get("peak_date_sales_amount"),
        },
        {"metric": "trend", "value": date_metrics.get("trend")},
        {
            "metric": "weekend_sales_lift_percent",
            "value": date_metrics.get("weekend_sales_lift_percent"),
        },
    ]
    pd.DataFrame(rows).to_excel(writer, sheet_name="Summary_结论", index=False)

    if ai_report:
        report_rows = [{"ai_report": line} for line in ai_report.splitlines()]
        startrow = len(rows) + 3
        pd.DataFrame(report_rows).to_excel(
            writer,
            sheet_name="Summary_结论",
            index=False,
            startrow=startrow,
        )


def _write_stocking_sheet(
    writer: pd.ExcelWriter,
    analysis_summary: dict[str, Any],
) -> None:
    tiers = analysis_summary.get("stocking_tiers", {})
    rows = []
    rows.extend(_with_tier(tiers.get("a_plus_core_products", []), "A+核心常备"))
    rows.extend(_with_tier(tiers.get("b_class_products", []), "B类商品"))
    rows.extend(
        _with_tier(analysis_summary.get("stocking_recommendations", []), "一般建议")
    )
    _write_table(
        writer,
        "备货建议",
        rows,
        [
            "tier",
            "product_code",
            "recommendation",
            "reason",
            "total_sales_amount",
            "total_quantity_sold",
            "sales_velocity",
            "covered_store_count",
        ],
    )


def _write_date_sheet(
    writer: pd.ExcelWriter,
    analysis_summary: dict[str, Any],
) -> None:
    date_metrics = analysis_summary.get("date_sales_relationship", {})
    sheet_name = "日期分析"
    startrow = 0
    startrow = _write_section(
        writer,
        sheet_name,
        "correlation_metrics",
        _correlation_rows(date_metrics.get("correlation_metrics", {})),
        startrow,
    )
    startrow = _write_section(
        writer,
        sheet_name,
        "weekend_vs_weekday",
        date_metrics.get("weekend_vs_weekday", []),
        startrow,
    )
    startrow = _write_section(
        writer,
        sheet_name,
        "top_sales_dates",
        date_metrics.get("top_sales_dates", []),
        startrow,
    )
    startrow = _write_section(
        writer,
        sheet_name,
        "lowest_sales_dates",
        date_metrics.get("lowest_sales_dates", []),
        startrow,
    )
    _write_section(
        writer,
        sheet_name,
        "daily_sales",
        date_metrics.get("daily_sales", []),
        startrow,
    )


def _write_section(
    writer: pd.ExcelWriter,
    sheet_name: str,
    title: str,
    rows: list[dict[str, Any]],
    startrow: int,
) -> int:
    title_df = pd.DataFrame([[title]])
    title_df.to_excel(
        writer,
        sheet_name=sheet_name,
        index=False,
        header=False,
        startrow=startrow,
    )
    table_df = pd.DataFrame(rows)
    if table_df.empty:
        table_df = pd.DataFrame([{"message": "No data"}])
    table_df.to_excel(
        writer,
        sheet_name=sheet_name,
        index=False,
        startrow=startrow + 1,
    )
    return startrow + len(table_df) + 4


def _write_table(
    writer: pd.ExcelWriter,
    sheet_name: str,
    rows: list[dict[str, Any]],
    columns: list[str],
) -> None:
    df = pd.DataFrame(rows)
    available_columns = [column for column in columns if column in df.columns]
    if df.empty:
        df = pd.DataFrame(columns=columns)
    elif available_columns:
        df = df[available_columns]
    df.to_excel(writer, sheet_name=sheet_name, index=False)


def _with_tier(rows: list[dict[str, Any]], tier: str) -> list[dict[str, Any]]:
    return [{**row, "tier": tier} for row in rows]


def _low_moving_rows(analysis_summary: dict[str, Any]) -> list[dict[str, Any]]:
    tiers = analysis_summary.get("stocking_tiers", {})
    return tiers.get("low_moving_products") or analysis_summary.get(
        "slow_moving_products", []
    )


def _correlation_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"metric": metric, "correlation": correlation}
        for metric, correlation in metrics.items()
    ]
