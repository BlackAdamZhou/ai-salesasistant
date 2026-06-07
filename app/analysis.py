from __future__ import annotations

import math
from typing import Any

import pandas as pd

from app.file_parser import parse_sales_dates


def prepare_sales_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    working = df.copy()
    required = ["date", "store_name", "product_code", "quantity_sold", "sales_amount"]
    missing = [column for column in required if column not in working.columns]
    if missing:
        raise ValueError(f"Missing columns for analysis: {', '.join(missing)}")

    working["date"] = parse_sales_dates(working["date"]).dt.normalize()
    working["quantity_sold"] = pd.to_numeric(working["quantity_sold"], errors="coerce")
    working["sales_amount"] = pd.to_numeric(working["sales_amount"], errors="coerce")
    if "stock_remaining" in working.columns:
        working["stock_remaining"] = pd.to_numeric(
            working["stock_remaining"], errors="coerce"
        )
    if "region" not in working.columns:
        working["region"] = "N/A"
    working["region"] = working["region"].fillna("N/A").astype(str).str.strip()
    working = working.dropna(subset=required)
    if working.empty:
        raise ValueError("No valid rows available for analysis.")
    return working


def build_analysis_summary(df: pd.DataFrame) -> dict[str, Any]:
    working = prepare_sales_dataframe(df)
    has_stock_column = "stock_remaining" in working.columns
    store_performance = calculate_store_performance(working)
    product_performance = calculate_product_performance(working)
    top_products = sorted(
        product_performance,
        key=lambda item: item["total_sales_amount"],
        reverse=True,
    )[:10]
    fast_moving_products = sorted(
        product_performance,
        key=lambda item: item["sales_velocity"],
        reverse=True,
    )[:10]
    slow_moving_products = sorted(
        product_performance,
        key=lambda item: item["sales_velocity"],
    )[:10]
    stocking_recommendations = generate_stocking_recommendations(product_performance)
    stocking_classification = classify_stocking_products(product_performance)
    date_sales_relationship = calculate_date_sales_relationship(working)

    return {
        "row_count": int(len(working)),
        "product_count": int(working["product_code"].nunique()),
        "store_count": int(working["store_name"].nunique()),
        "has_stock_column": has_stock_column,
        "date_range": {
            "start_date": _format_date(working["date"].min()),
            "end_date": _format_date(working["date"].max()),
            "sales_days": int(working["date"].nunique()),
        },
        "store_performance": store_performance,
        "top_products": top_products,
        "fast_moving_products": fast_moving_products,
        "slow_moving_products": slow_moving_products,
        "stocking_recommendations": stocking_recommendations,
        "stocking_classification": stocking_classification,
        "date_sales_relationship": date_sales_relationship,
    }


def calculate_store_performance(df: pd.DataFrame) -> list[dict[str, Any]]:
    store_region = (
        df.groupby(["store_name", "region"])
        .size()
        .reset_index(name="row_count")
        .sort_values(["store_name", "row_count"], ascending=[True, False])
        .drop_duplicates("store_name")[["store_name", "region"]]
    )
    grouped = (
        df.groupby("store_name")
        .agg(
            total_sales_amount=("sales_amount", "sum"),
            total_quantity_sold=("quantity_sold", "sum"),
            transaction_count=("sales_amount", "count"),
            sales_days=("date", "nunique"),
        )
        .reset_index()
    )
    grouped["average_daily_sales"] = (
        grouped["total_sales_amount"] / grouped["sales_days"].replace(0, pd.NA)
    )

    daily_by_store = (
        df.groupby(["store_name", "date"], as_index=False)["sales_amount"].sum()
    )
    idx = daily_by_store.groupby("store_name")["sales_amount"].idxmax()
    best_days = daily_by_store.loc[idx].rename(
        columns={"date": "best_sales_date", "sales_amount": "best_day_sales"}
    )
    result = grouped.merge(store_region, on="store_name", how="left").merge(
        best_days, on="store_name", how="left"
    )
    result = result.sort_values("total_sales_amount", ascending=False)
    return _records(result)


def calculate_product_performance(df: pd.DataFrame) -> list[dict[str, Any]]:
    aggregations: dict[str, tuple[str, str]] = {
        "total_quantity_sold": ("quantity_sold", "sum"),
        "total_sales_amount": ("sales_amount", "sum"),
        "sales_frequency": ("sales_amount", "count"),
        "sales_days": ("date", "nunique"),
        "covered_store_count": ("store_name", "nunique"),
        "average_sales_amount": ("sales_amount", "mean"),
    }
    if "stock_remaining" in df.columns:
        aggregations["average_stock_remaining"] = ("stock_remaining", "mean")

    grouped = df.groupby("product_code").agg(**aggregations).reset_index()
    grouped["average_daily_quantity"] = (
        grouped["total_quantity_sold"] / grouped["sales_days"].replace(0, pd.NA)
    )
    grouped["sales_velocity"] = grouped["average_daily_quantity"]
    grouped["single_store_daily_quantity"] = (
        grouped["total_quantity_sold"]
        / grouped["covered_store_count"].replace(0, pd.NA)
        / grouped["sales_days"].replace(0, pd.NA)
    )
    grouped = grouped.sort_values("total_sales_amount", ascending=False)
    return _records(grouped)


def generate_stocking_recommendations(
    product_performance: list[dict[str, Any]]
) -> list[dict[str, str]]:
    if not product_performance:
        return []

    metrics = pd.DataFrame(product_performance)
    velocity_q75 = metrics["sales_velocity"].quantile(0.75)
    velocity_q25 = metrics["sales_velocity"].quantile(0.25)
    revenue_q75 = metrics["total_sales_amount"].quantile(0.75)
    stock_q25 = (
        metrics["average_stock_remaining"].quantile(0.25)
        if "average_stock_remaining" in metrics.columns
        else None
    )

    recommendations: list[dict[str, str]] = []
    for item in product_performance:
        velocity = item["sales_velocity"]
        revenue = item["total_sales_amount"]
        stock = item.get("average_stock_remaining")

        if (
            stock_q25 is not None
            and stock is not None
            and not pd.isna(stock)
            and velocity >= velocity_q75
            and stock <= stock_q25
        ):
            recommendation = "Immediate restock"
            reason = "High sales velocity and comparatively low remaining stock."
        elif velocity >= velocity_q75 and revenue >= revenue_q75:
            recommendation = "Increase stock level"
            reason = "Strong sales velocity and high revenue contribution."
        elif velocity <= velocity_q25:
            recommendation = "Reduce future purchase volume"
            reason = "Low sales velocity compared with the rest of the assortment."
        else:
            recommendation = "Maintain current stock level"
            reason = "Sales velocity is within the normal range."

        recommendations.append(
            {
                "product_code": str(item["product_code"]),
                "recommendation": recommendation,
                "reason": reason,
            }
        )

    return recommendations


def classify_stocking_products(
    product_performance: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    if not product_performance:
        return {
            "a_plus_core_products": [],
            "b_class_products": [],
            "low_moving_products": [],
        }

    metrics = pd.DataFrame(product_performance)
    velocity_q75 = metrics["sales_velocity"].quantile(0.75)
    velocity_q25 = metrics["sales_velocity"].quantile(0.25)
    revenue_q75 = metrics["total_sales_amount"].quantile(0.75)
    revenue_q25 = metrics["total_sales_amount"].quantile(0.25)

    classes: dict[str, list[dict[str, Any]]] = {
        "a_plus_core_products": [],
        "b_class_products": [],
        "low_moving_products": [],
    }
    for item in product_performance:
        classification_item = {
            "product_code": item["product_code"],
            "total_sales_amount": item.get("total_sales_amount"),
            "total_quantity_sold": item.get("total_quantity_sold"),
            "sales_velocity": item.get("sales_velocity"),
            "covered_store_count": item.get("covered_store_count"),
            "sales_days": item.get("sales_days"),
            "single_store_daily_quantity": item.get("single_store_daily_quantity"),
        }
        revenue = item["total_sales_amount"]
        velocity = item["sales_velocity"]

        if revenue >= revenue_q75 and velocity >= velocity_q75:
            classification_item["stocking_action"] = (
                "3-day rolling replenishment plus safety stock"
            )
            classes["a_plus_core_products"].append(classification_item)
        elif revenue <= revenue_q25 or velocity <= velocity_q25:
            classification_item["stocking_action"] = (
                "Reduce proactive replenishment and monitor sell-through"
            )
            classes["low_moving_products"].append(classification_item)
        else:
            classification_item["stocking_action"] = (
                "Maintain store-level replenishment based on recent sales"
            )
            classes["b_class_products"].append(classification_item)

    for key, products in classes.items():
        classes[key] = sorted(
            products,
            key=lambda item: (
                item.get("total_sales_amount") or 0,
                item.get("sales_velocity") or 0,
            ),
            reverse=True,
        )
    return classes


def calculate_date_sales_relationship(df: pd.DataFrame) -> dict[str, Any]:
    aggregations: dict[str, tuple[str, str]] = {
        "sales_amount": ("sales_amount", "sum"),
        "quantity_sold": ("quantity_sold", "sum"),
        "transaction_count": ("sales_amount", "count"),
        "active_store_count": ("store_name", "nunique"),
        "active_product_count": ("product_code", "nunique"),
    }
    daily = (
        df.groupby("date", as_index=False)
        .agg(**aggregations)
        .sort_values("date")
    )

    peak_row = daily.loc[daily["sales_amount"].idxmax()]
    midpoint = max(len(daily) // 2, 1)
    first_half_avg = daily.iloc[:midpoint]["sales_amount"].mean()
    second_half_avg = daily.iloc[midpoint:]["sales_amount"].mean()
    if pd.isna(second_half_avg):
        second_half_avg = first_half_avg

    if second_half_avg > first_half_avg * 1.05:
        trend = "upward"
    elif second_half_avg < first_half_avg * 0.95:
        trend = "downward"
    else:
        trend = "stable"

    day_index = range(len(daily))
    correlation = _safe_corr(day_index, daily["sales_amount"])

    daily["day_type"] = daily["date"].dt.dayofweek.apply(
        lambda day: "weekend" if day >= 5 else "weekday"
    )
    weekend_vs_weekday = (
        daily.groupby("day_type", as_index=False)
        .agg(
            average_sales_amount=("sales_amount", "mean"),
            total_sales_amount=("sales_amount", "sum"),
            day_count=("date", "count"),
        )
        .sort_values("day_type")
    )
    weekend_avg = _lookup_day_type_average(weekend_vs_weekday, "weekend")
    weekday_avg = _lookup_day_type_average(weekend_vs_weekday, "weekday")
    weekend_lift = (
        ((weekend_avg - weekday_avg) / weekday_avg) * 100
        if weekday_avg and weekend_avg is not None
        else None
    )

    correlation_metrics = {
        "sales_amount": _safe_corr(day_index, daily["sales_amount"]),
        "quantity_sold": _safe_corr(day_index, daily["quantity_sold"]),
        "transaction_count": _safe_corr(day_index, daily["transaction_count"]),
        "active_store_count": _safe_corr(day_index, daily["active_store_count"]),
        "active_product_count": _safe_corr(day_index, daily["active_product_count"]),
    }

    return {
        "peak_date": _format_date(peak_row["date"]),
        "peak_date_sales_amount": _round_number(peak_row["sales_amount"]),
        "trend": trend,
        "date_sales_correlation": correlation,
        "correlation_metrics": correlation_metrics,
        "top_sales_dates": _records(daily.nlargest(3, "sales_amount")),
        "lowest_sales_dates": _records(daily.nsmallest(3, "sales_amount")),
        "weekend_sales_lift_percent": (
            _round_number(weekend_lift) if weekend_lift is not None else None
        ),
        "weekend_vs_weekday": _records(weekend_vs_weekday),
        "daily_sales": _records(daily.drop(columns=["day_type"])),
    }


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    output = []
    for record in df.to_dict(orient="records"):
        cleaned: dict[str, Any] = {}
        for key, value in record.items():
            if isinstance(value, pd.Timestamp):
                cleaned[key] = _format_date(value)
            elif pd.isna(value):
                cleaned[key] = None
            elif isinstance(value, float):
                cleaned[key] = _round_number(value)
            else:
                cleaned[key] = value.item() if hasattr(value, "item") else value
        output.append(cleaned)
    return output


def _format_date(value: Any) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _round_number(value: Any) -> float:
    return round(float(value), 4)


def _safe_corr(day_index: range, values: pd.Series) -> float:
    if len(values) <= 1 or values.nunique(dropna=True) <= 1:
        return 0.0
    correlation = float(pd.Series(day_index).corr(values))
    if math.isnan(correlation):
        return 0.0
    return round(correlation, 4)


def _lookup_day_type_average(df: pd.DataFrame, day_type: str) -> float | None:
    row = df.loc[df["day_type"] == day_type]
    if row.empty:
        return None
    return float(row.iloc[0]["average_sales_amount"])
