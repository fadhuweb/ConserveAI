# Nigerian Wildlife Forecasting

Live multi-threat forecasting and budget-constrained intervention recommendation for Nigerian national parks.

## What it does

1. Produces daily 30-day threat probability forecasts (fire, drought, vegetation degradation) for six national parks.
2. Recommends how to spend a park's conservation budget within constraints, updating in real time.

## Parks covered

Yankari, Cross River, Gashaka-Gumti, Kainji Lake, Chad Basin, Old Oyo — roughly 23,000 km² across savanna, rainforest, wetland, and Sahel ecosystems.

## Stack

- **Backend**: FastAPI + PostgreSQL + APScheduler
- **ML**: Random Forest, XGBoost, LSTM, Transformer (supervised + semi-supervised)
- **Optimizer**: PuLP (integer linear programming)
- **Frontend**: React + Leaflet + Recharts
- **Data**: Open-Meteo, NASA POWER, Google Earth Engine, NASA FIRMS

## Setup

```bash
cp .env.example .env
# fill in API keys

python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

See [docs/deployment_guide.md](docs/deployment_guide.md) for full setup.

## Demo accounts

| Username | Role |
|---|---|
| yankari_manager | Yankari park manager |
| cross_river_manager | Cross River park manager |
| gashaka_manager | Gashaka-Gumti park manager |
| kainji_manager | Kainji Lake park manager |
| chad_basin_manager | Chad Basin park manager |
| old_oyo_manager | Old Oyo park manager |
| national_admin | Read-only national overview |
| examiner | Thesis evaluation access |

## License

MIT
