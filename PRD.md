# AI Sales Operations Assistant PRD

Source PRD was provided at:

```text
C:/Users/28042/Downloads/Codex_PRD_AI_Sales_Operations_Assistant.md
```

This repository implements the backend MVP described there:

- FastAPI API with `/health`, `/analyze-sales`, and debug-only
  `/product-mapping`.
- CSV and Excel upload support.
- Chinese/English column alias mapping and Excel header-row detection.
- Data cleaning, product-name anonymisation, sales analytics, stocking
  recommendations, and date-sales relationship analysis.
- OpenAI report generation with local fallback when no API key is configured.
- Docker and pytest support.
