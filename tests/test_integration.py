from pathlib import Path

from app.ai_service import generate_fallback_report
from app.analysis import build_analysis_summary
from app.anonymizer import anonymise_product_names
from app.file_parser import read_sales_file


def test_full_pipeline_with_sample_csv():
    path = Path("data/sample_sales.csv")
    cleaned = read_sales_file(path.name, path.read_bytes())
    anonymised, mapping = anonymise_product_names(cleaned)
    summary = build_analysis_summary(anonymised)
    report = generate_fallback_report(summary)

    assert mapping
    assert summary["store_performance"]
    assert summary["top_products"]
    assert "Executive Summary" in report
    assert "Coca Cola" not in report
    assert "Jasmine Rice" not in report
    assert "Potato Chips" not in report

