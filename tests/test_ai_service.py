import pytest

from app.ai_service import generate_ai_report


def _summary():
    return {
        "row_count": 1,
        "product_count": 1,
        "store_count": 1,
        "store_performance": [],
        "top_products": [],
        "fast_moving_products": [],
        "slow_moving_products": [],
        "stocking_recommendations": [],
        "date_sales_relationship": {},
    }


def test_generate_ai_report_can_use_local_provider():
    output = generate_ai_report(_summary(), provider="local")

    assert output["provider"] == "local"
    assert output["model"] == "local-rule-based"
    assert output["language"] == "en"
    assert output["used_fallback"] is True
    assert "Which Stores Perform Well" in output["report"]


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
