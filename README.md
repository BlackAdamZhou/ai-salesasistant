# AI Sales Operations Assistant

Backend MVP for analysing retail POS sales files and generating AI-assisted
operations insights. The project is built for a GitHub-ready internship
portfolio demo and is usable from FastAPI Swagger UI at `/docs`.

## Features

- Upload `.xlsx`, `.xls`, or `.csv` POS files.
- Detect Excel header rows when the first rows contain report titles.
- Map common Chinese and English POS column names to internal fields.
- Clean invalid dates, summary rows, missing values, and negative quantities.
- Anonymise product names before AI processing as `Product_001`, `Product_002`.
- Calculate store performance, top products, fast/slow movers, stocking actions,
  and date-sales relationships.
- Generate an AI report with user-selectable providers: `auto`, `deepseek`,
  `openai`, or `local`.
- Expose a debug-only product mapping endpoint for local testing.

## Tech Stack

Python, FastAPI, pandas, OpenAI API, Docker, pytest.

## Input Requirements

Required fields after column mapping:

| Internal field | Meaning |
| --- | --- |
| `date` | Sales or transaction date |
| `store_name` | Store or branch name |
| `product_name` | Product name |
| `quantity_sold` | Quantity sold |
| `sales_amount` | Sales amount or revenue |

Optional field:

| Internal field | Meaning |
| --- | --- |
| `stock_remaining` | Remaining stock |

The parser supports Chinese headers such as `营业日`, `门店名称`, `商品名称`,
`商品销售数量(销售)`, and `商品销售金额(销售)`.

## Privacy

Real product names are replaced with stable product codes before AI report
generation. The normal `/analyze-sales` response and OpenAI prompt do not include
the original product-name mapping.

`GET /product-mapping` is debug-only and should not be exposed in production.

## Local Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

Set `.env` only if you want live AI provider reports. DeepSeek is supported
through its OpenAI-compatible API:

```text
DEEPSEEK_API_KEY=your_deepseek_key_here
AI_BASE_URL=https://api.deepseek.com
AI_MODEL=deepseek-v4-flash
```

Optional AI limits can be added only when needed:

```text
AI_TIMEOUT_SECONDS=180
AI_MAX_RETRIES=2
AI_MAX_TOKENS=3000
```

If these variables are not set, the app does not add its own timeout or token
limit and uses the provider/SDK defaults.

OpenAI is also supported:

```text
OPENAI_API_KEY=your_openai_key_here
OPENAI_MODEL=gpt-4o-mini
```

Without a valid API key, the app returns a local fallback report.

## Docker Run

```bash
docker compose up --build
```

Then open:

```text
http://127.0.0.1:8000/docs
```

## API

### `GET /health`

```json
{
  "status": "ok",
  "service": "AI Sales Operations Assistant"
}
```

### `POST /analyze-sales`

Upload a `.xlsx`, `.xls`, or `.csv` file using form field `file`.

Optional form fields:

| Field | Default | Description |
| --- | --- | --- |
| `ai_provider` | `auto` | Use `auto`, `deepseek`, `openai`, or `local` |
| `ai_model` | Provider default | Optional model override |
| `ai_base_url` | Provider default | Optional OpenAI-compatible base URL |
| `output_language` | `en` | Use `en` / `english` / `英文`, or `zh` / `chinese` / `中文` |

Provider behavior:

- `auto`: uses DeepSeek if `DEEPSEEK_API_KEY` exists, otherwise OpenAI.
- `deepseek`: uses `DEEPSEEK_API_KEY`, `AI_BASE_URL`, and `AI_MODEL`.
- `openai`: uses `OPENAI_API_KEY` and `OPENAI_MODEL`.
- `local`: skips external AI and returns the rule-based fallback report.

Example response shape:

```json
{
  "anonymisation_status": "completed",
  "row_count": 1500,
  "product_count": 45,
  "store_performance": [],
  "top_products": [],
  "fast_moving_products": [],
  "slow_moving_products": [],
  "stocking_recommendations": [],
  "date_sales_relationship": {},
  "ai_output": {
    "provider": "deepseek",
    "model": "deepseek-v4-flash",
    "base_url": "https://api.deepseek.com",
    "language": "en",
    "used_fallback": false,
    "error": null,
    "report": "## 1. Which Stores Perform Well..."
  },
  "ai_report": "## 1. Which Stores Perform Well..."
}
```

### `GET /product-mapping`

Returns the latest in-memory product mapping for local debugging only.

## Tests

```bash
pytest
```

## Resume Description

AI Sales Operations Assistant | Python, FastAPI, pandas, OpenAI API, Docker

- Built a backend prototype that analyses retail POS data and generates
  AI-assisted business insights.
- Implemented product-name anonymisation before sending data to the AI model to
  improve data privacy.
- Used pandas to calculate store performance, top-selling products, sales
  velocity, date-based sales trends, and stocking recommendations.
- Integrated OpenAI API to generate structured business reports for retail
  operations.
- Developed REST API endpoints with FastAPI and containerised the application
  using Docker.
