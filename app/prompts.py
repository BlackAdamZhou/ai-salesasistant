from __future__ import annotations

import json
from typing import Any


REPORT_SECTIONS = [
    "1. Which Stores Perform Well",
    "2. Which Products Sell Well",
    "3. Which Products Move Quickly",
    "4. Stocking Recommendations",
    "5. Relationship Between Sales Data and Dates",
]

CHINESE_REPORT_SECTIONS = [
    "1. 哪些店铺业绩好",
    "2. 哪些商品销售好",
    "3. 哪些商品周转快",
    "4. 备货建议",
    "5. 销售数据与日期的关联度",
]


def normalise_output_language(output_language: str) -> str:
    language = output_language.strip().lower()
    chinese_values = {"zh", "zh-cn", "chinese", "中文", "cn"}
    english_values = {"en", "en-us", "english", "英文"}

    if language in chinese_values:
        return "zh"
    if language in english_values:
        return "en"
    raise ValueError("Unsupported output_language. Use 'zh' for Chinese or 'en' for English.")


def build_sales_report_prompt(
    summary: dict[str, Any],
    output_language: str = "en",
) -> str:
    sales_summary = json.dumps(summary, ensure_ascii=False, indent=2)
    language = normalise_output_language(output_language)
    if language == "zh":
        sections = "\n".join(CHINESE_REPORT_SECTIONS)
        return f"""你是一名 AI 销售运营分析师。

数据集已经完成匿名化处理。商品名称只会以 Product_001 等商品代码展示。不要推断或还原原始商品名称。

请分析以下销售摘要，并生成清晰的中文业务报告。报告必须严格围绕下面 5 个章节输出：

{sections}

格式要求：
- 使用 Markdown。
- 每个章节都要有明确结论。
- 门店业绩章节请优先给出按销售额排名前 10 的门店表格，列包括：排名、门店、区域、销售额、销量、日均销售额。
- 商品销售章节请给出按销售额排名前 10 的商品表格，列包括：排名、商品代码、销售额、销量、覆盖门店。
- 商品周转章节请说明如果没有库存字段，则不能计算严格库存周转率，并用销量、销售次数、覆盖门店、活跃天数、单店日均销量综合判断动销速度。请给出前 10 商品表格。
- 备货建议章节请分为 A+ 核心常备商品、B 类商品、低动销商品。商品只能使用匿名商品代码。建议包含“3天滚动补货 + 安全库存”的运营建议；如果没有库存字段，请说明需要结合门店历史销量和实际库存执行。
- 日期关联章节请给出相关系数表，包含销售额、销量、销售次数、活跃门店数、活跃商品数；解释周末与工作日差异，并列出销售额最高和最低日期。
- 不要编造真实商品名称。不要输出商品匿名映射。
- 使用适合零售运营经理阅读的中文业务语言。解释原因要清楚，报告要简洁、实用。

销售摘要：
{sales_summary}
"""

    sections = "\n".join(REPORT_SECTIONS)
    return f"""You are an AI sales operations analyst.

The dataset has already been anonymised. Product names are represented only as product codes such as Product_001. Do not infer or reconstruct original product names.

Analyse the following sales summary and generate a clear English business report. The report must strictly follow these 5 sections:

{sections}

Formatting requirements:
- Use Markdown.
- Each section must include a clear conclusion.
- In the store performance section, include a top 10 store table ranked by sales amount with columns: rank, store, region, sales amount, quantity sold, average daily sales.
- In the product sales section, include a top 10 product table ranked by sales amount with columns: rank, product code, sales amount, quantity sold, covered stores.
- In the product velocity section, explain that strict inventory turnover cannot be calculated if no stock column exists. Use quantity sold, sales frequency, covered stores, active days, and single-store daily quantity as the proxy for movement speed. Include a top 10 product table.
- In the stocking recommendations section, split recommendations into A+ core always-in-stock products, B class products, and slow-moving products. Use anonymised product codes only. Include a practical "3-day rolling replenishment + safety stock" recommendation; if no stock field exists, explain that store-level history and actual stock should be combined before execution.
- In the date relationship section, include a correlation table covering sales amount, quantity sold, transaction count, active store count, and active product count. Explain weekend versus weekday differences and list the highest and lowest sales dates.
- Do not invent real product names. Do not output the product anonymisation mapping.
- Use practical business language. Explain the reasoning clearly. Keep the report concise and suitable for an operations manager.

Sales summary:
{sales_summary}
"""
