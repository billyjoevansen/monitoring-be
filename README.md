# Simpubes Serang — Backend API

Backend API untuk Sistem Informasi Monitoring Pupuk Bersubsidi Kota Serang.

## Tech Stack

- Python 3.12+
- Flask 3.1
- scikit-learn (Random Forest Classifier)
- pandas / openpyxl
- Supabase (PostgreSQL)
- matplotlib (visualization)

## Setup

1. Clone repository
2. Create virtual environment: `python -m venv venv && source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill in the values
5. Run: `python app.py`

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase service role key |
| `CORS_ORIGINS` | Comma-separated allowed origins (default: localhost) |
| `FLASK_DEBUG` | Set to `true` for development (default: `false`) |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/reconcile` | Reconcile RDKK vs SIVERVAL |
| POST | `/api/train` | Train Random Forest model |
| POST | `/api/predict` | Predict from 2 files |
| POST | `/api/classify` | Classify from reconciliation archive |
| GET | `/api/model/info` | Get trained model info |
| GET | `/api/config` | Get model configuration |
| PUT | `/api/config` | Update model configuration |
| POST | `/api/config/reset` | Reset config to default |

## Testing

```bash
pytest tests/ -v
```
