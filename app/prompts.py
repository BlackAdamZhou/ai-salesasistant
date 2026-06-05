from __future__ import annotations

import json
from typing import Any


REPORT_SECTIONS = [
    "Executive Summary",
    "Store Performance Analysis",
    "Best-Selling Products",
    "Fast-Moving Products",
    "Slow-Moving Products",
    "Stocking Recommendations",
    "Relationship Between Sales and Date",
    "Business Risks",
    "Recommended Next Actions",
]


def build_sales_report_prompt(summary: dict[str, Any]) -> str:
    sales_summary = json.dumps(summary, ensure_ascii=False, indent=2)
    return f"""You are an AI sales operations analyst.

The dataset has already been anonymised. Product names are represented only as product codes such as Product_001. Do not infer or reconstruct original product names.

Analyse the following sales summary and generate a clear business report.

Required sections:
1. Executive Summary
2. Store Performance Analysis
3. Best-Selling Products
4. Fast-Moving Products
5. Slow-Moving Products
6. Stocking Recommendations
7. Relationship Between Sales and Date
8. Business Risks
9. Recommended Next Actions

Use practical business language. Explain the reasoning clearly. Keep the report concise and suitable for an operations manager.

Sales summary:
{sales_summary}
"""

