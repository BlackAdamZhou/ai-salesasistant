# AI Sales Operations Assistant

[English](#English) | [中文](#中文)

## English

Backend MVP for analysing retail POS sales files and generating AI-assisted
operations insights. The project is usable from FastAPI Swagger UI at `/docs`.

### Features

- Upload `.xlsx` or `.csv` POS files.
- Detect Excel header rows when the first rows contain report titles.
- Map common Chinese and English POS column names to internal fields.
- Clean invalid dates, summary rows, missing values, and negative quantities.
- Anonymise product names before AI processing as `Product_001`, `Product_002`.
- Calculate store performance, top products, fast/slow movers, stocking actions,
  and date-sales relationships.
- Classify stocking into A+ core products, B class products, and low-moving
  products.
- Rank product sales Top 10 by sales amount, not by unit quantity.
- Generate an AI report with user-selectable providers: `auto`, `deepseek`,
  `openai`, or `local`.
- Export the anonymised analysis workbook from `/export-analysis`.
- Expose a debug-only product mapping endpoint for local testing.

### Tech Stack

Python, FastAPI, pandas, OpenAI API, Docker, pytest.

### Input Requirements

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

When `stock_remaining` is absent, the report states that strict inventory
turnover cannot be calculated and uses sales velocity proxies instead.

The parser supports Chinese headers such as `营业日`, `门店名称`, `商品名称`,
`商品销售数量(销售)`, and `商品销售金额(销售)`.

### Privacy

Real product names are replaced with stable product codes before AI report
generation. The normal `/analyze-sales` response and OpenAI prompt do not include
the original product-name mapping.

`GET /product-mapping` is debug-only and should not be exposed in production.

### Local Run

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

Without a valid API key, the app returns a local Markdown fallback report with
Top 10 tables, stocking tiers, correlation metrics, and highest/lowest sales
dates.

### Docker Run

```bash
docker compose up --build
```

Then open:

```text
http://127.0.0.1:8000/docs
```

### API

#### `GET /health`

```json
{
  "status": "ok",
  "service": "AI Sales Operations Assistant"
}
```

#### `POST /analyze-sales`

Upload a `.xlsx` or `.csv` file using form field `file`.

Optional form fields:

| Field | Default | Description |
| --- | --- | --- |
| `ai_provider` | `auto` | Use `auto`, `deepseek`, `openai`, or `local` |
| `ai_model` | Provider default | Optional model override |
| `ai_base_url` | Provider default | Optional OpenAI-compatible base URL |
| `output_language` | `zh` | Use `zh` / `chinese` / `中文`, or `en` / `english` / `英文` |

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
  "stocking_tiers": {
    "a_plus_core_products": [],
    "b_class_products": [],
    "low_moving_products": []
  },
  "stocking_recommendations": [],
  "date_sales_relationship": {},
  "ai_output": {
    "provider": "deepseek",
    "model": "deepseek-v4-flash",
    "base_url": "https://api.deepseek.com",
    "language": "zh",
    "used_fallback": false,
    "error": null,
    "report": "## 1. 哪些店铺业绩好..."
  },
  "ai_report": "## 1. 哪些店铺业绩好..."
}
```

### `POST /export-analysis`

Upload a `.xlsx` or `.csv` file using form field `file`. The endpoint
returns an Excel workbook with sheets: `Summary_结论`, `门店表现`, `商品销售额`,
`动销速度`, `备货建议`, `低动销商品`, `日期分析`, and `区域表现`.

#### `GET /product-mapping`

Returns the latest in-memory product mapping for local debugging only.

### Tests

```bash
py -m pytest -q
```

Latest local verification:

```text
21 passed in 3.31s
```



## 销售数据分析助手

[English](#English) | [中文](#中文)

## 中文

零售 POS 销售文件分析后端 MVP，可生成 AI 辅助的运营洞察。本项目作为可以通过 FastAPI Swagger UI 的 `/docs` 页面使用。

### 功能特性

- 支持上传 `.xlsx` 或 `.csv` POS 文件。
- 当 Excel 前几行包含报表标题时，可自动识别真实表头行。
- 将常见中英文 POS 列名映射为内部字段。
- 清洗无效日期、汇总行、缺失值和负数销量。
- 在 AI 处理前将真实商品名匿名化为 `Product_001`、`Product_002` 等稳定编码。
- 计算门店表现、热销商品、快慢动销商品、补货建议和日期销售关系。
- 商品销售 Top 10 按销售额排名，而不是按销量排名。
- 将备货结构化分类为 A+ 核心常备商品、B 类商品和低动销商品。
- 支持通过 `auto`、`deepseek`、`openai` 或 `local` 选择 AI 报告生成方式。
- 可从 `/export-analysis` 导出匿名化分析 Excel 工作簿。
- 提供仅用于本地测试的商品映射调试接口。

### 技术栈

Python、FastAPI、pandas、OpenAI API、Docker、pytest。

### 输入要求

列名映射后必须包含以下字段：

| 内部字段 | 含义 |
| --- | --- |
| `date` | 销售或交易日期 |
| `store_name` | 门店或分店名称 |
| `product_name` | 商品名称 |
| `quantity_sold` | 销售数量 |
| `sales_amount` | 销售金额或收入 |

可选字段：

| 内部字段 | 含义 |
| --- | --- |
| `stock_remaining` | 剩余库存 |

解析器支持 `营业日`、`门店名称`、`商品名称`、`商品销售数量(销售)`、
`商品销售金额(销售)` 等中文表头。

### 隐私保护

在生成 AI 报告之前，真实商品名会被替换为稳定的商品编码。正常的
`/analyze-sales` 响应和 OpenAI 提示词不会包含原始商品名映射。

`GET /product-mapping` 仅用于调试，不应在生产环境中暴露。

### 本地运行

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

打开：

```text
http://127.0.0.1:8000/docs
```

只有在需要真实 AI 服务商报告时才需要配置 `.env`。DeepSeek 通过
OpenAI 兼容 API 支持：

```text
DEEPSEEK_API_KEY=your_deepseek_key_here
AI_BASE_URL=https://api.deepseek.com
AI_MODEL=deepseek-v4-flash
```

可按需添加 AI 限制配置：

```text
AI_TIMEOUT_SECONDS=180
AI_MAX_RETRIES=2
AI_MAX_TOKENS=3000
```

如果未设置这些变量，应用不会额外添加超时或 token 限制，而是使用服务商
或 SDK 的默认值。

同时支持 OpenAI：

```text
OPENAI_API_KEY=your_openai_key_here
OPENAI_MODEL=gpt-4o-mini
```

如果没有有效 API Key，应用会返回本地规则生成的 Markdown 兜底报告，
包含 Top 10 表格、备货分类、相关系数和最高/最低销售日期。

### Docker 运行

```bash
docker compose up --build
```

然后打开：

```text
http://127.0.0.1:8000/docs
```

### API

#### `GET /health`

```json
{
  "status": "ok",
  "service": "AI Sales Operations Assistant"
}
```

#### `POST /analyze-sales`

使用表单字段 `file` 上传 `.xlsx` 或 `.csv` 文件。

可选表单字段：

| 字段 | 默认值 | 描述 |
| --- | --- | --- |
| `ai_provider` | `auto` | 使用 `auto`、`deepseek`、`openai` 或 `local` |
| `ai_model` | 服务商默认值 | 可选的模型覆盖配置 |
| `ai_base_url` | 服务商默认值 | 可选的 OpenAI 兼容 Base URL |
| `output_language` | `zh` | 使用 `zh` / `chinese` / `中文`，或 `en` / `english` / `英文` |

服务商行为：

- `auto`：如果存在 `DEEPSEEK_API_KEY` 则使用 DeepSeek，否则使用 OpenAI。
- `deepseek`：使用 `DEEPSEEK_API_KEY`、`AI_BASE_URL` 和 `AI_MODEL`。
- `openai`：使用 `OPENAI_API_KEY` 和 `OPENAI_MODEL`。
- `local`：跳过外部 AI，返回基于规则的兜底报告。

响应结构示例：

```json
{
  "anonymisation_status": "completed",
  "row_count": 1500,
  "product_count": 45,
  "store_performance": [],
  "top_products": [],
  "fast_moving_products": [],
  "slow_moving_products": [],
  "stocking_tiers": {
    "a_plus_core_products": [],
    "b_class_products": [],
    "low_moving_products": []
  },
  "stocking_recommendations": [],
  "date_sales_relationship": {},
  "ai_output": {
    "provider": "deepseek",
    "model": "deepseek-v4-flash",
    "base_url": "https://api.deepseek.com",
    "language": "zh",
    "used_fallback": false,
    "error": null,
    "report": "## 1. 哪些店铺业绩好..."
  },
  "ai_report": "## 1. 哪些店铺业绩好..."
}
```

### `POST /export-analysis`

使用表单字段 `file` 上传 `.xlsx` 或 `.csv` 文件。接口返回 Excel 工作簿，
包含 `Summary_结论`、`门店表现`、`商品销售额`、`动销速度`、`备货建议`、
`低动销商品`、`日期分析` 和 `区域表现` 等工作表。

#### `GET /product-mapping`

返回最近一次内存中的商品映射，仅用于本地调试。

### 测试

```bash
py -m pytest -q
```

最近一次本地验证结果：

```text
21 passed in 3.31s
```
