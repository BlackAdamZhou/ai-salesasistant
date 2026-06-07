from __future__ import annotations

from io import BytesIO

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.ai_service import generate_ai_report
from app.analysis import build_analysis_summary
from app.anonymizer import anonymise_product_names
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
        description="Report language: en / english / 英文, or zh / chinese / 中文.",
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
            has_stock_column=analysis_summary["has_stock_column"],
            store_performance=analysis_summary["store_performance"],
            top_products=analysis_summary["top_products"],
            fast_moving_products=analysis_summary["fast_moving_products"],
            slow_moving_products=analysis_summary["slow_moving_products"],
            stocking_recommendations=analysis_summary["stocking_recommendations"],
            stocking_classification=analysis_summary["stocking_classification"],
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


@app.get("/product-mapping", response_model=ProductMappingResponse)
def product_mapping() -> ProductMappingResponse:
    return ProductMappingResponse(
        warning=(
            "Debug-only endpoint. Do not expose original product names in production."
        ),
        mapping=_latest_product_mapping,
    )


@app.post("/export-analysis")
async def export_analysis(file: UploadFile = File(...)) -> StreamingResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a name.")

    try:
        content = await file.read()
        cleaned = read_sales_file(file.filename, content)
        anonymised, _ = anonymise_product_names(cleaned)
        summary = build_analysis_summary(anonymised)
        workbook = _build_analysis_workbook(summary)
        return StreamingResponse(
            workbook,
            media_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": (
                    'attachment; filename="sales_analysis_export.xlsx"'
                )
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise HTTPException(
            status_code=500, detail=f"Failed to export sales analysis: {exc}"
        ) from exc


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
        "products_top_10_by_sales_amount": sorted(
            summary.get("top_products", []),
            key=lambda item: item.get("total_sales_amount", 0),
            reverse=True,
        )[:10],
        "fast_moving_products_top_10": summary.get("fast_moving_products", [])[:10],
        "slow_moving_products_bottom_10": summary.get("slow_moving_products", [])[:10],
        "stocking_recommendations_sample": summary.get(
            "stocking_recommendations", []
        )[:20],
        "stocking_classification": {
            key: values[:10]
            for key, values in summary.get("stocking_classification", {}).items()
        },
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


def _build_analysis_workbook(summary: dict) -> BytesIO:
    output = BytesIO()
    date_metrics = summary.get("date_sales_relationship", {})
    stocking = summary.get("stocking_classification", {})

    sheets: dict[str, pd.DataFrame] = {
        "Summary_结论": pd.DataFrame(
            [
                {"metric": "row_count", "value": summary.get("row_count")},
                {"metric": "product_count", "value": summary.get("product_count")},
                {"metric": "store_count", "value": summary.get("store_count")},
                {"metric": "has_stock_column", "value": summary.get("has_stock_column")},
                {
                    "metric": "date_range_start",
                    "value": summary.get("date_range", {}).get("start_date"),
                },
                {
                    "metric": "date_range_end",
                    "value": summary.get("date_range", {}).get("end_date"),
                },
                {"metric": "sales_trend", "value": date_metrics.get("trend")},
                {"metric": "peak_date", "value": date_metrics.get("peak_date")},
            ]
        ),
        "门店表现": pd.DataFrame(summary.get("store_performance", [])),
        "商品销售额": pd.DataFrame(summary.get("top_products", [])),
        "动销速度": pd.DataFrame(summary.get("fast_moving_products", [])),
        "备货建议": pd.DataFrame(
            stocking.get("a_plus_core_products", [])
            + stocking.get("b_class_products", [])
        ),
        "低动销商品": pd.DataFrame(stocking.get("low_moving_products", [])),
        "日期分析": pd.DataFrame(date_metrics.get("daily_sales", [])),
        "区域表现": _build_region_performance_frame(summary.get("store_performance", [])),
    }

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
            worksheet = writer.sheets[sheet_name]
            worksheet.freeze_panes = "A2"
            for column_cells in worksheet.columns:
                max_length = max(
                    len(str(cell.value)) if cell.value is not None else 0
                    for cell in column_cells
                )
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(
                    max(max_length + 2, 12), 32
                )

    output.seek(0)
    return output


def _build_region_performance_frame(store_performance: list[dict]) -> pd.DataFrame:
    if not store_performance:
        return pd.DataFrame()
    frame = pd.DataFrame(store_performance)
    if "region" not in frame.columns:
        return pd.DataFrame()
    return (
        frame.groupby("region", as_index=False)
        .agg(
            total_sales_amount=("total_sales_amount", "sum"),
            total_quantity_sold=("total_quantity_sold", "sum"),
            store_count=("store_name", "nunique"),
            average_daily_sales=("average_daily_sales", "mean"),
        )
        .sort_values("total_sales_amount", ascending=False)
    )
