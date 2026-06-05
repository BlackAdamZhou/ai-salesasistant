from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile

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
async def analyze_sales(file: UploadFile = File(...)) -> AnalyzeSalesResponse:
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
        ai_report = generate_ai_report(ai_input_summary)

        return AnalyzeSalesResponse(
            anonymisation_status="completed",
            row_count=analysis_summary["row_count"],
            product_count=analysis_summary["product_count"],
            store_performance=analysis_summary["store_performance"],
            top_products=analysis_summary["top_products"],
            fast_moving_products=analysis_summary["fast_moving_products"],
            slow_moving_products=analysis_summary["slow_moving_products"],
            stocking_recommendations=analysis_summary["stocking_recommendations"],
            date_sales_relationship=analysis_summary["date_sales_relationship"],
            ai_report=ai_report,
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


def _build_ai_safe_summary(summary: dict) -> dict:
    allowed_keys = {
        "row_count",
        "product_count",
        "store_count",
        "store_performance",
        "top_products",
        "fast_moving_products",
        "slow_moving_products",
        "stocking_recommendations",
        "date_sales_relationship",
    }
    return {key: value for key, value in summary.items() if key in allowed_keys}

