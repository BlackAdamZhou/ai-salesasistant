from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str


class StockingRecommendation(BaseModel):
    product_code: str
    recommendation: str
    reason: str


class AIOutput(BaseModel):
    provider: str
    model: str
    base_url: str | None = None
    language: str
    used_fallback: bool
    error: str | None = None
    provider_response_id: str | None = None
    usage: dict[str, int | None] | None = None
    report: str


class AnalyzeSalesResponse(BaseModel):
    anonymisation_status: str = Field(default="completed")
    row_count: int
    product_count: int
    store_performance: list[dict[str, Any]]
    top_products: list[dict[str, Any]]
    fast_moving_products: list[dict[str, Any]]
    slow_moving_products: list[dict[str, Any]]
    stocking_recommendations: list[StockingRecommendation]
    date_sales_relationship: dict[str, Any]
    ai_output: AIOutput
    ai_report: str


class ProductMappingResponse(BaseModel):
    warning: str
    mapping: dict[str, str]
