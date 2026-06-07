from __future__ import annotations

from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.ai_service import generate_ai_report
from app.analysis import build_analysis_summary
from app.anonymizer import anonymise_product_names
from app.exporter import XLSX_MEDIA_TYPE, build_analysis_workbook
from app.file_parser import read_sales_file
from app.schemas import AnalyzeSalesResponse, HealthResponse, ProductMappingResponse


app = FastAPI(
    title="AI Sales Operations Assistant",
    description=(
        "Analyse retail POS files, anonymise product names, and generate "
        "AI-assisted operations insights."
    ),
    version="0.1.0",
)

_latest_product_mapping: dict[str, str] = {}


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="AI Sales Operations Assistant")


@app.post("/analyze-sales", response_model=AnalyzeSalesResponse)
async def analyze_sales(
    file: UploadFile = File(...),
    ai_provider: str = Form(
        default="auto",
        description="AI provider: auto, deepseek, openai, or local.",
    ),
    ai_model: str | None = Form(
        default=None,
        description="Optional model override, such as deepseek-v4-flash or gpt-4o-mini.",
    ),
    ai_base_url: str | None = Form(
        default=None,
        description="Optional OpenAI-compatible base URL override.",
    ),
    output_language: str = Form(
        default="zh",
        description="Report language: zh / chinese / 中文, or en / english / 英文.",
    ),
) -> AnalyzeSalesResponse:
    global _latest_product_mapping

    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a name.")

    try:
        content = await file.read()
        cleaned = read_sales_file(file.filename, content)
        anonymised, mapping = anonymise_product_names(cleaned)
        _latest_product_mapping = mapping

        analysis_summary = build_analysis_summary(anonymised)
        ai_input_summary = _build_ai_safe_summary(analysis_summary)
        ai_output = generate_ai_report(
            ai_input_summary,
            provider=ai_provider,
            model=ai_model,
            base_url=ai_base_url,
            output_language=output_language,
        )

        return AnalyzeSalesResponse(
            anonymisation_status="completed",
            row_count=analysis_summary["row_count"],
            product_count=analysis_summary["product_count"],
            store_count=analysis_summary["store_count"],
            has_stock_column=analysis_summary["has_stock_column"],
            store_performance=analysis_summary["store_performance"],
            region_performance=analysis_summary["region_performance"],
            top_products=analysis_summary["top_products"],
            fast_moving_products=analysis_summary["fast_moving_products"],
            slow_moving_products=analysis_summary["slow_moving_products"],
            stocking_tiers=analysis_summary["stocking_tiers"],
            stocking_recommendations=analysis_summary["stocking_recommendations"],
            date_sales_relationship=analysis_summary["date_sales_relationship"],
            ai_output=ai_output,
            ai_report=ai_output["report"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise HTTPException(
            status_code=500, detail=f"Failed to analyse sales file: {exc}"
        ) from exc


@app.post(
    "/export-analysis",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Downloadable Excel analysis workbook.",
            "content": {XLSX_MEDIA_TYPE: {}},
        }
    },
)
async def export_analysis(
    file: UploadFile = File(...),
    ai_provider: str = Form(
        default="local",
        description="AI provider: auto, deepseek, openai, or local.",
    ),
    ai_model: str | None = Form(
        default=None,
        description="Optional model override, such as deepseek-v4-flash or gpt-4o-mini.",
    ),
    ai_base_url: str | None = Form(
        default=None,
        description="Optional OpenAI-compatible base URL override.",
    ),
    output_language: str = Form(
        default="zh",
        description="Report language: zh / chinese / 中文, or en / english / 英文.",
    ),
) -> StreamingResponse:
    global _latest_product_mapping

    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a name.")

    try:
        content = await file.read()
        cleaned = read_sales_file(file.filename, content)
        anonymised, mapping = anonymise_product_names(cleaned)
        _latest_product_mapping = mapping

        analysis_summary = build_analysis_summary(anonymised)
        ai_input_summary = _build_ai_safe_summary(analysis_summary)
        ai_output = generate_ai_report(
            ai_input_summary,
            provider=ai_provider,
            model=ai_model,
            base_url=ai_base_url,
            output_language=output_language,
        )
        workbook = build_analysis_workbook(
            analysis_summary,
            ai_report=ai_output["report"],
        )
        filename = _analysis_export_filename(analysis_summary)
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        }
        return StreamingResponse(
            workbook,
            media_type=XLSX_MEDIA_TYPE,
            headers=headers,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise HTTPException(
            status_code=500, detail=f"Failed to export sales analysis: {exc}"
        ) from exc


@app.get("/product-mapping", response_model=ProductMappingResponse)
def product_mapping() -> ProductMappingResponse:
    return ProductMappingResponse(
        warning=(
            "Debug-only endpoint. Do not expose original product names in production."
        ),
        mapping=_latest_product_mapping,
    )


def _build_ai_safe_summary(summary: dict) -> dict:
    date_metrics = summary.get("date_sales_relationship", {})
    return {
        "row_count": summary.get("row_count"),
        "product_count": summary.get("product_count"),
        "store_count": summary.get("store_count"),
        "has_stock_column": summary.get("has_stock_column"),
        "date_range": summary.get("date_range"),
        "store_performance_top_10_by_sales_amount": summary.get(
            "store_performance", []
        )[:10],
        "region_performance_top_10_by_sales_amount": summary.get(
            "region_performance", []
        )[:10],
        "products_top_10_by_sales_amount": sorted(
            summary.get("top_products", []),
            key=lambda item: item.get("total_sales_amount", 0),
            reverse=True,
        )[:10],
        "fast_moving_products_top_10": summary.get("fast_moving_products", [])[:10],
        "slow_moving_products_bottom_10": summary.get("slow_moving_products", [])[:10],
        "stocking_tiers": summary.get("stocking_tiers", {}),
        "stocking_recommendations_sample": summary.get(
            "stocking_recommendations", []
        )[:20],
        "date_sales_relationship": {
            "peak_date": date_metrics.get("peak_date"),
            "peak_date_sales_amount": date_metrics.get("peak_date_sales_amount"),
            "trend": date_metrics.get("trend"),
            "date_sales_correlation": date_metrics.get("date_sales_correlation"),
            "correlation_metrics": date_metrics.get("correlation_metrics"),
            "weekend_sales_lift_percent": date_metrics.get(
                "weekend_sales_lift_percent"
            ),
            "weekend_vs_weekday": date_metrics.get("weekend_vs_weekday"),
            "top_sales_dates": date_metrics.get("top_sales_dates"),
            "lowest_sales_dates": date_metrics.get("lowest_sales_dates"),
        },
    }


def _analysis_export_filename(summary: dict) -> str:
    date_range = summary.get("date_range", {})
    start_date = date_range.get("start_date")
    end_date = date_range.get("end_date")
    if start_date and end_date:
        return f"ai_sales_analysis_{start_date}_{end_date}.xlsx"
    return "ai_sales_analysis.xlsx"
