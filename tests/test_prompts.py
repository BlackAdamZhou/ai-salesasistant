from app.prompts import build_sales_report_prompt


def test_chinese_prompt_uses_requested_business_structure():
    prompt = build_sales_report_prompt({"row_count": 1}, output_language="zh")

    assert "哪些店铺业绩好" in prompt
    assert "哪些商品销售好" in prompt
    assert "哪些商品周转快" in prompt
    assert "备货建议" in prompt
    assert "销售数据与日期的关联度" in prompt
    assert "不要推断或还原原始商品名称" in prompt


def test_english_prompt_uses_requested_business_structure():
    prompt = build_sales_report_prompt({"row_count": 1}, output_language="en")

    assert "Which Stores Perform Well" in prompt
    assert "Which Products Sell Well" in prompt
    assert "Which Products Move Quickly" in prompt
    assert "Stocking Recommendations" in prompt
    assert "Relationship Between Sales Data and Dates" in prompt
    assert "Do not infer or reconstruct original product names" in prompt
