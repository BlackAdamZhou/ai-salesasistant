import pandas as pd

from app.analysis import (
    build_analysis_summary,
    calculate_date_sales_relationship,
    calculate_product_performance,
    calculate_region_performance,
    calculate_store_performance,
    classify_stocking_tiers,
    generate_stocking_recommendations,
)


def _df():
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-04-01",
                    "2026-04-01",
                    "2026-04-02",
                    "2026-04-03",
                    "2026-04-04",
                ]
            ),
            "store_name": ["Store A", "Store A", "Store B", "Store B", "Store A"],
            "region": ["Region 1", "Region 1", "Region 2", "Region 2", "Region 1"],
            "product_code": [
                "Product_001",
                "Product_002",
                "Product_001",
                "Product_001",
                "Product_003",
            ],
            "quantity_sold": [10, 2, 8, 12, 1],
            "sales_amount": [100, 30, 80, 120, 5],
            "stock_remaining": [4, 40, 5, 2, 60],
        }
    )


def test_calculate_store_performance_ranks_by_sales_amount():
    result = calculate_store_performance(_df())

    assert result[0]["store_name"] == "Store B"
    assert result[0]["region"] == "Region 2"
    assert result[0]["total_sales_amount"] == 200.0
    assert result[0]["best_sales_date"] == "2026-04-03"


def test_calculate_region_performance_ranks_by_sales_amount():
    result = calculate_region_performance(_df())

    assert result[0]["region"] == "Region 2"
    assert result[0]["total_sales_amount"] == 200.0
    assert result[0]["store_count"] == 1


def test_calculate_product_performance_includes_velocity():
    result = calculate_product_performance(_df())
    product_001 = next(item for item in result if item["product_code"] == "Product_001")

    assert product_001["total_quantity_sold"] == 30
    assert product_001["sales_velocity"] == 10.0
    assert product_001["covered_store_count"] == 2
    assert product_001["single_store_daily_quantity"] == 5.0


def test_generate_stocking_recommendations_returns_actions():
    performance = calculate_product_performance(_df())
    recommendations = generate_stocking_recommendations(performance)

    assert recommendations
    assert {item["product_code"] for item in recommendations} == {
        "Product_001",
        "Product_002",
        "Product_003",
    }


def test_classify_stocking_tiers_returns_structured_groups():
    performance = calculate_product_performance(_df())
    tiers = classify_stocking_tiers(performance)

    assert set(tiers) == {
        "a_plus_core_products",
        "b_class_products",
        "low_moving_products",
    }
    assert tiers["a_plus_core_products"]


def test_calculate_date_sales_relationship_identifies_peak_and_trend():
    result = calculate_date_sales_relationship(_df())

    assert result["peak_date"] == "2026-04-01"
    assert result["trend"] in {"upward", "downward", "stable"}
    assert "correlation_metrics" in result
    assert "top_sales_dates" in result
    assert "lowest_sales_dates" in result
    assert result["daily_sales"]


def test_build_analysis_summary_has_required_sections():
    summary = build_analysis_summary(_df())

    assert summary["row_count"] == 5
    assert summary["has_stock_column"] is True
    assert summary["date_range"]["sales_days"] == 4
    assert summary["store_performance"]
    assert summary["region_performance"]
    assert summary["top_products"]
    assert summary["stocking_tiers"]
    assert summary["stocking_recommendations"]
    assert summary["date_sales_relationship"]["daily_sales"]


def test_build_analysis_summary_ranks_top_products_by_sales_amount():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-04-01", "2026-04-01"]),
            "store_name": ["Store A", "Store A"],
            "region": ["Region 1", "Region 1"],
            "product_code": ["Product_high_quantity", "Product_high_revenue"],
            "quantity_sold": [100, 1],
            "sales_amount": [100, 1000],
        }
    )

    summary = build_analysis_summary(df)

    assert summary["top_products"][0]["product_code"] == "Product_high_revenue"
