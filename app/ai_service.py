from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from app.prompts import build_sales_report_prompt


DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
SUPPORTED_AI_PROVIDERS = {"auto", "openai", "deepseek", "local"}


def generate_ai_report(
    summary: dict[str, Any],
    provider: str = "auto",
    model: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    load_dotenv()
    config = _load_ai_config(provider=provider, model=model, base_url=base_url)
    if config["provider"] == "local":
        report = generate_fallback_report(summary, "Local rule-based report selected.")
        return _build_ai_output(config, report, used_fallback=True, error=None)

    if not config["api_key"]:
        report = generate_fallback_report(
            summary, "No AI API key is configured. Set DEEPSEEK_API_KEY or OPENAI_API_KEY."
        )
        return _build_ai_output(
            config,
            report,
            used_fallback=True,
            error="No AI API key is configured.",
        )

    try:
        from openai import OpenAI

        client_kwargs = {"api_key": config["api_key"]}
        if config["base_url"]:
            client_kwargs["base_url"] = config["base_url"]

        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=config["model"],
            messages=[
                {
                    "role": "system",
                    "content": "You write concise retail operations reports.",
                },
                {"role": "user", "content": build_sales_report_prompt(summary)},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content
        if not content:
            report = generate_fallback_report(summary, "AI provider returned no text.")
            return _build_ai_output(
                config,
                report,
                used_fallback=True,
                error="AI provider returned no text.",
            )
        return _build_ai_output(config, content, used_fallback=False, error=None)
    except Exception as exc:  # pragma: no cover - depends on external API
        report = generate_fallback_report(summary, f"AI provider API call failed: {exc}")
        return _build_ai_output(config, report, used_fallback=True, error=str(exc))


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
    used_fallback: bool,
    error: str | None,
) -> dict[str, Any]:
    return {
        "provider": config["provider"],
        "model": config["model"],
        "base_url": config["base_url"],
        "used_fallback": used_fallback,
        "error": error,
        "report": report,
    }


def generate_fallback_report(summary: dict[str, Any], reason: str | None = None) -> str:
    stores = summary.get("store_performance", [])
    top_products = summary.get("top_products", [])
    fast_products = summary.get("fast_moving_products", [])
    slow_products = summary.get("slow_moving_products", [])
    recommendations = summary.get("stocking_recommendations", [])
    date_metrics = summary.get("date_sales_relationship", {})

    best_store = stores[0] if stores else {}
    best_product = top_products[0] if top_products else {}
    peak_date = date_metrics.get("peak_date", "N/A")
    trend = date_metrics.get("trend", "stable")

    report = [
        "## 1. Executive Summary",
        (
            f"Analysed {summary.get('row_count', 0)} sales rows across "
            f"{summary.get('store_count', 0)} stores and "
            f"{summary.get('product_count', 0)} anonymised products. "
            f"The strongest store by revenue is {best_store.get('store_name', 'N/A')}."
        ),
        "## 2. Store Performance Analysis",
        (
            f"Top store revenue: {best_store.get('total_sales_amount', 0)}; "
            f"quantity sold: {best_store.get('total_quantity_sold', 0)}; "
            f"best sales date: {best_store.get('best_sales_date', 'N/A')}."
        ),
        "## 3. Best-Selling Products",
        (
            f"Best-selling product code by quantity is "
            f"{best_product.get('product_code', 'N/A')} with "
            f"{best_product.get('total_quantity_sold', 0)} units sold."
        ),
        "## 4. Fast-Moving Products",
        _product_codes_sentence(fast_products, "Fast-moving product codes"),
        "## 5. Slow-Moving Products",
        _product_codes_sentence(slow_products, "Slow-moving product codes"),
        "## 6. Stocking Recommendations",
        _recommendations_sentence(recommendations),
        "## 7. Relationship Between Sales and Date",
        (
            f"Peak sales date is {peak_date}. The overall date-sales trend is "
            f"{trend}, based on first-half versus second-half average daily sales."
        ),
        "## 8. Business Risks",
        (
            "High-velocity products may face stockout risk if replenishment does "
            "not match demand. Slow-moving products may increase holding cost."
        ),
        "## 9. Recommended Next Actions",
        (
            "Prioritise replenishment for high-velocity and high-revenue product "
            "codes, review slow movers before the next purchasing cycle, and "
            "compare peak sales dates with store staffing and promotion plans."
        ),
    ]
    if reason:
        report.append(f"\n_Local fallback report used: {reason}_")
    return "\n\n".join(report)


def _product_codes_sentence(products: list[dict[str, Any]], label: str) -> str:
    codes = [str(item.get("product_code")) for item in products[:5]]
    return f"{label}: {', '.join(codes) if codes else 'N/A'}."


def _recommendations_sentence(recommendations: list[dict[str, Any]]) -> str:
    if not recommendations:
        return "No stocking recommendations were generated."
    priority = recommendations[:5]
    return "Priority actions: " + "; ".join(
        f"{item['product_code']} - {item['recommendation']}" for item in priority
    )
