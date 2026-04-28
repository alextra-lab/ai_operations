# Admin Pricing API (ADR-046)

Base path: `/api/v1/admin/pricing`

Endpoints

- `GET /models/{model_id}/pricing/current` — current effective price
- `GET /models/{model_id}/pricing/history` — list of price records
- `POST /models/{model_id}/pricing/change` — create new price record

Example response

```json
{
  "model_id": "mistral-large",
  "currency": "EUR",
  "input_price_per_million": 2.98,
  "output_price_per_million": 12.01,
  "effective_from": "2025-10-01T00:00:00Z",
  "effective_to": null
}
```

Notes

- Prices are EUR per 1M tokens.
- History records are immutable; updates create new records.
- Cost estimator consumes current price when available; falls back to
  model registry/env defaults.
