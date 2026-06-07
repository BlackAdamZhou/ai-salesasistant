import pytest

from app.ai_service import generate_ai_report, generate_fallback_report


def _summary():
    return {
        "row_count": 1,
        "product_count": 1,
        "store_count": 1,
        "has_stock_column": False,
        "store_performance": [],
        "region_performance": [],
        "top_products": [],
        "fast_moving_products": [],
        "slow_moving_products": [],
        "stocking_tiers": {
            "a_plus_core_products": [],
            "b_class_products": [],
            "low_moving_products": [],
        },
        "stocking_recommendations": [],
        "date_sales_relationship": {},
    }


def test_generate_ai_report_can_use_local_provider():
    output = generate_ai_report(_summary(), provider="local")

    assert output["provider"] == "local"
    assert output["model"] == "local-rule-based"
    assert output["language"] == "zh"
    assert output["used_fallback"] is True
    assert "哪些店铺业绩好" in output["report"]


def test_generate_ai_report_can_use_chinese_output():
    output = generate_ai_report(_summary(), provider="local", output_language="中文")

    assert output["language"] == "zh"
    assert output["used_fallback"] is True
    assert "哪些店铺业绩好" in output["report"]


def test_generate_ai_report_rejects_unknown_provider():
    with pytest.raises(ValueError):
        generate_ai_report(_summary(), provider="unknown")


def test_generate_ai_report_rejects_unknown_language():
    with pytest.raises(ValueError):
        generate_ai_report(_summary(), provider="local", output_language="spanish")


def test_generate_fallback_report_accepts_ai_safe_summary():
    compact_summary = {
        "row_count": 10,
        "product_count": 2,
        "store_count": 1,
        "store_performance_top_10_by_sales_amount": [
            {
                "store_name": "Store A",
                "region": "Region 1",
                "total_sales_amount": 1000,
                "total_quantity_sold": 50,
                "average_daily_sales": 500,
            }
        ],
        "products_top_10_by_sales_amount": [
            {
                "product_code": "Product_001",
                "total_sales_amount": 800,
                "total_quantity_sold": 40,
                "covered_store_count": 1,
            }
        ],
        "fast_moving_products_top_10": [
            {
                "product_code": "Product_001",
                "sales_velocity": 20,
                "total_quantity_sold": 40,
                "sales_frequency": 2,
                "sales_days": 2,
                "single_store_daily_quantity": 20,
            }
        ],
        "slow_moving_products_bottom_10": [],
        "stocking_tiers": {
            "a_plus_core_products": [
                {
                    "product_code": "Product_001",
                    "total_sales_amount": 800,
                    "total_quantity_sold": 40,
                    "sales_velocity": 20,
                    "covered_store_count": 1,
                    "reason": "High revenue and velocity.",
                }
            ],
            "b_class_products": [],
            "low_moving_products": [],
        },
        "stocking_recommendations_sample": [
            {
                "product_code": "Product_001",
                "recommendation": "Increase stock level",
                "reason": "Strong sales.",
            }
        ],
        "date_sales_relationship": {
            "peak_date": "2026-04-01",
            "trend": "stable",
            "correlation_metrics": {"sales_amount": 0.5},
            "top_sales_dates": [{"date": "2026-04-01", "sales_amount": 1000}],
            "lowest_sales_dates": [{"date": "2026-04-02", "sales_amount": 100}],
        },
    }

    report = generate_fallback_report(compact_summary, output_language="zh")

    assert "哪些店铺业绩好" in report
    assert "Product_001" in report
    assert "| 排名 |" in report
