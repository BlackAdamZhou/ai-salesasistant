from pathlib import Path

from app.ai_service import generate_fallback_report
from app.analysis import build_analysis_summary
from app.anonymizer import anonymise_product_names
from app.file_parser import read_sales_file
from app.main import _build_ai_safe_summary


def test_full_pipeline_with_sample_csv():
    path = Path("data/sample_sales.csv")
    cleaned = read_sales_file(path.name, path.read_bytes())
    anonymised, mapping = anonymise_product_names(cleaned)
    summary = build_analysis_summary(anonymised)
    report = generate_fallback_report(summary)

    assert mapping
    assert summary["store_performance"]
    assert summary["top_products"]
    assert "Which Stores Perform Well" in report
    assert "Coca Cola" not in report
    assert "Jasmine Rice" not in report
    assert "Potato Chips" not in report


def test_ai_safe_summary_is_compact():
    summary = {
        "row_count": 100,
        "product_count": 20,
        "store_count": 30,
        "date_range": {"sales_days": 19},
        "store_performance": [{"store_name": str(index)} for index in range(30)],
        "top_products": [
            {"product_code": f"Product_{index:03d}", "total_sales_amount": index}
            for index in range(30)
        ],
        "fast_moving_products": [{"product_code": str(index)} for index in range(30)],
        "slow_moving_products": [{"product_code": str(index)} for index in range(30)],
        "stocking_recommendations": [
            {"product_code": str(index), "recommendation": "Maintain", "reason": "x"}
            for index in range(30)
        ],
        "date_sales_relationship": {
            "peak_date": "2026-04-01",
            "daily_sales": [{"date": str(index)} for index in range(30)],
            "top_sales_dates": [{"date": "2026-04-01"}],
            "lowest_sales_dates": [{"date": "2026-04-02"}],
        },
    }

    ai_summary = _build_ai_safe_summary(summary)

    assert len(ai_summary["store_performance_top_10_by_sales_amount"]) == 10
    assert len(ai_summary["products_top_10_by_sales_amount"]) == 10
    assert len(ai_summary["stocking_recommendations_sample"]) == 20
    assert "daily_sales" not in ai_summary["date_sales_relationship"]
