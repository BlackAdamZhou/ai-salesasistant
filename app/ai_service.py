from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from app.prompts import build_sales_report_prompt, normalise_output_language


DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
SUPPORTED_AI_PROVIDERS = {"auto", "openai", "deepseek", "local"}


def generate_ai_report(
    summary: dict[str, Any],
    provider: str = "auto",
    model: str | None = None,
    base_url: str | None = None,
    output_language: str = "zh",
) -> dict[str, Any]:
    load_dotenv()
    language = normalise_output_language(output_language)
    config = _load_ai_config(provider=provider, model=model, base_url=base_url)
    if config["provider"] == "local":
        report = generate_fallback_report(
            summary, "Local rule-based report selected.", output_language=language
        )
        return _build_ai_output(config, report, language, used_fallback=True, error=None)

    if not config["api_key"]:
        report = generate_fallback_report(
            summary,
            "No AI API key is configured. Set DEEPSEEK_API_KEY or OPENAI_API_KEY.",
            output_language=language,
        )
        return _build_ai_output(
            config,
            report,
            language,
            used_fallback=True,
            error="No AI API key is configured.",
        )

    try:
        from openai import OpenAI

        client_kwargs = {"api_key": config["api_key"]}
        timeout = os.getenv("AI_TIMEOUT_SECONDS")
        if timeout:
            client_kwargs["timeout"] = float(timeout)
        max_retries = os.getenv("AI_MAX_RETRIES")
        if max_retries:
            client_kwargs["max_retries"] = int(max_retries)
        if config["base_url"]:
            client_kwargs["base_url"] = config["base_url"]

        client = OpenAI(**client_kwargs)
        completion_kwargs: dict[str, Any] = {
            "model": config["model"],
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You write concise retail operations reports. "
                        "Always follow the requested output language."
                    ),
                },
                {
                    "role": "user",
                    "content": build_sales_report_prompt(
                        summary, output_language=language
                    ),
                },
            ],
            "temperature": 0.2,
        }
        max_tokens = os.getenv("AI_MAX_TOKENS")
        if max_tokens:
            completion_kwargs["max_tokens"] = int(max_tokens)

        response = client.chat.completions.create(**completion_kwargs)
        content = response.choices[0].message.content
        if not content:
            report = generate_fallback_report(
                summary, "AI provider returned no text.", output_language=language
            )
            return _build_ai_output(
                config,
                report,
                language,
                used_fallback=True,
                error="AI provider returned no text.",
            )
        return _build_ai_output(
            config,
            content,
            language,
            used_fallback=False,
            error=None,
            provider_response_id=getattr(response, "id", None),
            usage=_extract_usage(response),
        )
    except Exception as exc:  # pragma: no cover - depends on external API
        report = generate_fallback_report(
            summary, f"AI provider API call failed: {exc}", output_language=language
        )
        return _build_ai_output(
            config, report, language, used_fallback=True, error=str(exc)
        )


def _load_ai_config(
    provider: str = "auto",
    model: str | None = None,
    base_url: str | None = None,
) -> dict[str, str | None]:
    provider = provider.strip().lower() or "auto"
    model = model.strip() if model else None
    base_url = base_url.strip() if base_url else None
    if provider not in SUPPORTED_AI_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_AI_PROVIDERS))
        raise ValueError(f"Unsupported ai_provider '{provider}'. Use one of: {supported}.")

    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if provider == "local":
        return {
            "provider": "local",
            "api_key": None,
            "base_url": None,
            "model": "local-rule-based",
        }

    if provider == "deepseek" or (provider == "auto" and deepseek_key):
        return {
            "provider": "deepseek",
            "api_key": deepseek_key,
            "base_url": base_url or os.getenv("AI_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL),
            "model": model or os.getenv("AI_MODEL", DEFAULT_DEEPSEEK_MODEL),
        }

    return {
        "provider": "openai",
        "api_key": openai_key,
        "base_url": base_url or os.getenv("OPENAI_BASE_URL"),
        "model": model or os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
    }


def _build_ai_output(
    config: dict[str, str | None],
    report: str,
    language: str,
    used_fallback: bool,
    error: str | None,
    provider_response_id: str | None = None,
    usage: dict[str, int | None] | None = None,
) -> dict[str, Any]:
    return {
        "provider": config["provider"],
        "model": config["model"],
        "base_url": config["base_url"],
        "language": language,
        "used_fallback": used_fallback,
        "error": error,
        "provider_response_id": provider_response_id,
        "usage": usage,
        "report": report,
    }


def _extract_usage(response: Any) -> dict[str, int | None] | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def generate_fallback_report(
    summary: dict[str, Any],
    reason: str | None = None,
    output_language: str = "zh",
) -> str:
    language = normalise_output_language(output_language)
    stores = summary.get("store_performance", [])
    top_products = summary.get("top_products", [])
    fast_products = summary.get("fast_moving_products", [])
    slow_products = summary.get("slow_moving_products", [])
    stocking_tiers = summary.get("stocking_tiers", {})
    recommendations = summary.get("stocking_recommendations", [])
    date_metrics = summary.get("date_sales_relationship", {})

    best_store = stores[0] if stores else {}
    best_product = top_products[0] if top_products else {}
    peak_date = date_metrics.get("peak_date", "N/A")
    trend = date_metrics.get("trend", "stable")

    if language == "zh":
        report = [
            "## 1. 哪些店铺业绩好",
            (
                f"本次共分析 {summary.get('row_count', 0)} 条销售记录，覆盖 "
                f"{summary.get('store_count', 0)} 家门店和 "
                f"{summary.get('product_count', 0)} 个匿名商品。"
                f"销售额表现最好的门店是 {best_store.get('store_name', 'N/A')}。"
            ),
            (
                f"头部门店销售额为 {best_store.get('total_sales_amount', 0)}，"
                f"区域为 {best_store.get('region', 'N/A')}，"
                f"销售数量为 {best_store.get('total_quantity_sold', 0)}，"
                f"最佳销售日期为 {best_store.get('best_sales_date', 'N/A')}。"
            ),
            _markdown_table(
                stores[:10],
                [
                    ("门店", "store_name"),
                    ("区域", "region"),
                    ("销售额", "total_sales_amount"),
                    ("销量", "total_quantity_sold"),
                    ("日均销售额", "average_daily_sales"),
                ],
                rank=True,
            ),
            "## 2. 哪些商品销售好",
            (
                f"按销售额计算，表现最好的商品代码是 "
                f"{best_product.get('product_code', 'N/A')}，销售额为 "
                f"{best_product.get('total_sales_amount', 0)}，销量为 "
                f"{best_product.get('total_quantity_sold', 0)}。"
            ),
            _markdown_table(
                top_products[:10],
                [
                    ("商品代码", "product_code"),
                    ("销售额", "total_sales_amount"),
                    ("销量", "total_quantity_sold"),
                    ("覆盖门店", "covered_store_count"),
                ],
                rank=True,
            ),
            "## 3. 哪些商品周转快",
            (
                "如无库存字段，无法计算严格库存周转率。可用销量、销售次数、"
                "覆盖门店、活跃天数和单店日均销量综合判断动销速度。"
            ),
            _markdown_table(
                fast_products[:10],
                [
                    ("商品代码", "product_code"),
                    ("动销速度", "sales_velocity"),
                    ("销量", "total_quantity_sold"),
                    ("销售次数", "sales_frequency"),
                    ("活跃天数", "sales_days"),
                    ("单店日均销量", "single_store_daily_quantity"),
                ],
                rank=True,
            ),
            "## 4. 备货建议",
            (
                "A+ 核心常备商品应优先保证不断货，建议采用 3 天滚动补货并叠加"
                "安全库存；B 类商品按门店历史销量分配；低动销商品减少主动铺货。"
            ),
            "### A+ 核心常备商品",
            _markdown_table(
                stocking_tiers.get("a_plus_core_products", []),
                _tier_columns(),
                rank=True,
            ),
            "### B 类商品",
            _markdown_table(
                stocking_tiers.get("b_class_products", []),
                _tier_columns(),
                rank=True,
            ),
            "### 低动销商品",
            _markdown_table(
                stocking_tiers.get("low_moving_products", []),
                _tier_columns(),
                rank=True,
            ),
            _recommendations_sentence(recommendations, output_language=language),
            "## 5. 销售数据与日期的关联度",
            (
                f"销售峰值日期是 {peak_date}。基于前半段与后半段日均销售额对比，"
                f"整体销售趋势为 {trend}。"
            ),
            _correlation_table(date_metrics.get("correlation_metrics", {}), language),
            "### 最高销售日期 Top 3",
            _markdown_table(
                date_metrics.get("top_sales_dates", []),
                _date_sales_columns(),
                rank=True,
            ),
            "### 最低销售日期 Top 3",
            _markdown_table(
                date_metrics.get("lowest_sales_dates", []),
                _date_sales_columns(),
                rank=True,
            ),
        ]
        if reason:
            report.append(f"\n_已使用本地规则报告：{reason}_")
        return "\n\n".join(report)

    report = [
        "## 1. Which Stores Perform Well",
        (
            f"Analysed {summary.get('row_count', 0)} sales rows across "
            f"{summary.get('store_count', 0)} stores and "
            f"{summary.get('product_count', 0)} anonymised products. "
            f"The strongest store by revenue is {best_store.get('store_name', 'N/A')}."
        ),
        (
            f"Top store revenue: {best_store.get('total_sales_amount', 0)}; "
            f"region: {best_store.get('region', 'N/A')}; "
            f"quantity sold: {best_store.get('total_quantity_sold', 0)}; "
            f"best sales date: {best_store.get('best_sales_date', 'N/A')}."
        ),
        "## 2. Which Products Sell Well",
        (
            f"Top-selling product code by sales amount is "
            f"{best_product.get('product_code', 'N/A')} with "
            f"{best_product.get('total_sales_amount', 0)} in sales and "
            f"{best_product.get('total_quantity_sold', 0)} units sold."
        ),
        "## 3. Which Products Move Quickly",
        (
            "Strict inventory turnover cannot be calculated without stock data. "
            "Use quantity sold, sales frequency, covered stores, active days, and "
            "single-store daily quantity as movement-speed proxies."
        ),
        _product_codes_sentence(fast_products, "Fast-moving product codes"),
        "## 4. Stocking Recommendations",
        (
            "A+ core products should be protected from stockouts with 3-day rolling "
            "replenishment plus safety stock. B class products should be allocated "
            "by store-level history. Slow movers should receive less proactive stock."
        ),
        _recommendations_sentence(recommendations),
        "## 5. Relationship Between Sales Data and Dates",
        (
            f"Peak sales date is {peak_date}. The overall date-sales trend is "
            f"{trend}, based on first-half versus second-half average daily sales."
        ),
    ]
    if reason:
        report.append(f"\n_Local fallback report used: {reason}_")
    return "\n\n".join(report)


def _product_codes_sentence(products: list[dict[str, Any]], label: str) -> str:
    codes = [str(item.get("product_code")) for item in products[:5]]
    return f"{label}: {', '.join(codes) if codes else 'N/A'}."


def _recommendations_sentence(
    recommendations: list[dict[str, Any]],
    output_language: str = "zh",
) -> str:
    if not recommendations:
        if normalise_output_language(output_language) == "zh":
            return "未生成补货建议。"
        return "No stocking recommendations were generated."
    priority = recommendations[:5]
    if normalise_output_language(output_language) == "zh":
        return "优先动作：" + "；".join(
            f"{item['product_code']} - {item['recommendation']}" for item in priority
        )
    return "Priority actions: " + "; ".join(
        f"{item['product_code']} - {item['recommendation']}" for item in priority
    )


def _tier_columns() -> list[tuple[str, str]]:
    return [
        ("商品代码", "product_code"),
        ("销售额", "total_sales_amount"),
        ("销量", "total_quantity_sold"),
        ("动销速度", "sales_velocity"),
        ("覆盖门店", "covered_store_count"),
        ("原因", "reason"),
    ]


def _date_sales_columns() -> list[tuple[str, str]]:
    return [
        ("日期", "date"),
        ("销售额", "sales_amount"),
        ("销量", "quantity_sold"),
        ("销售次数", "transaction_count"),
        ("活跃门店", "active_store_count"),
        ("活跃商品", "active_product_count"),
    ]


def _markdown_table(
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str]],
    rank: bool = False,
) -> str:
    if not rows:
        return "暂无数据。"

    headers = [label for label, _ in columns]
    if rank:
        headers = ["排名", *headers]
    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for index, row in enumerate(rows, start=1):
        values = [_format_table_value(row.get(key)) for _, key in columns]
        if rank:
            values = [str(index), *values]
        output.append("| " + " | ".join(values) + " |")
    return "\n".join(output)


def _correlation_table(metrics: dict[str, Any], output_language: str) -> str:
    if not metrics:
        return "暂无相关系数数据。"
    labels = {
        "sales_amount": "销售额" if output_language == "zh" else "Sales amount",
        "quantity_sold": "销量" if output_language == "zh" else "Quantity sold",
        "transaction_count": (
            "销售次数" if output_language == "zh" else "Transaction count"
        ),
        "active_store_count": (
            "活跃门店数" if output_language == "zh" else "Active store count"
        ),
        "active_product_count": (
            "活跃商品数" if output_language == "zh" else "Active product count"
        ),
    }
    rows = [
        {"metric": labels.get(key, key), "correlation": value}
        for key, value in metrics.items()
    ]
    return _markdown_table(rows, [("指标", "metric"), ("相关系数", "correlation")])


def _format_table_value(value: Any) -> str:
    if value is None:
        return "N/A"
    return str(value).replace("|", "\\|")
