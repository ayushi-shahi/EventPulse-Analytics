# EventPulse Analytics Platform

Real-time event ingestion and analytics platform with alerts, metrics, and WebSocket streaming.

## Features

- **High-Throughput Ingestion**: Handle thousands of events per second
- **Real-Time Analytics**: Live metrics computed every minute
- **Smart Alerts**: Configurable thresholds with cooldown periods
- **WebSocket Streaming**: Real-time event and alert delivery
- **REST API**: Complete API for all operations
- **Scalable Architecture**: Async processing with Celery workers

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (recommended)

## Quick Start (Docker)

### 1. Clone and Setup

```bash
git clone https://github.com/yourusername/eventpulse-analytics.git
cd eventpulse-analytics/backend
cp .env.example .env
# Edit .env with your configuration
```

### 2. Start Services

```bash
docker-compose up --build
```

### 3. Access API

- **API Docs**: http://localhost:8002/docs
- **Health Check**: http://localhost:8002/api/v1/health/

## Local Development (Without Docker)

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Setup Database

```bash
# Create database
createdb EventPulse

# Run migrations
alembic upgrade head
```

### 3. Start Services

```bash
# Terminal 1: API
uvicorn app.main:app --reload

# Terminal 2: Celery Worker
celery -A worker.celery_app worker --loglevel=info --pool=solo

# Terminal 3: Celery Beat
celery -A beat.celery_app beat --loglevel=info
```

## API Documentation

### Authentication

```bash
# Register user
curl -X POST http://localhost:8002/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'

# Login
curl -X POST http://localhost:8002/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

### API Keys

```bash
# Create API key (requires JWT token)
curl -X POST http://localhost:8002/api/v1/api-keys/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"client_name":"My App","rate_limit":5000}'
```

### Event Ingestion

```bash
# Send single event
curl -X POST http://localhost:8002/api/v1/ingest/events \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"event_name":"page_view","user_id":"user123","properties":{"page":"/home"}}'

# Send batch
curl -X POST http://localhost:8002/api/v1/ingest/events/batch \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"events":[{"event_name":"click","user_id":"user456"}]}'
```

### Metrics

```bash
# Get overview
curl http://localhost:8002/api/v1/metrics/overview?period=last_hour \
  -H "X-API-Key: YOUR_API_KEY"

# Get time series
curl http://localhost:8000/api/v1/metrics/time-series/events_per_minute \
  -H "X-API-Key: YOUR_API_KEY"
```

### Alerts

```bash
# Create alert
curl -X POST http://localhost:8002/api/v1/alerts/ \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"High Traffic",
    "expression":{"metric":"events_per_minute","operator":">","threshold":1000},
    "severity":"warning"
  }'
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/unit/test_security.py -v
```

## Deployment

### Docker Production

```bash
# Build
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d

# Logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Cloud Platforms

#### Render

1. Create new Web Service
2. Connect GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables
6. Add PostgreSQL and Redis add-ons

#### AWS ECS

See `docs/deployment/aws-ecs.md`

#### DigitalOcean App Platform

See `docs/deployment/digitalocean.md`

## Architecture

```
Client Apps → API (FastAPI)
              ↓
         Redis Queue
              ↓
    Celery Workers → PostgreSQL
              ↓
    Redis Pub/Sub → WebSocket
```

## Security

- JWT authentication for platform users
- API key authentication for client apps
- Rate limiting (configurable per key)
- Password hashing with Argon2
- SQL injection protection (SQLAlchemy ORM)
- CORS configuration

## Performance

- **Ingestion**: 10,000+ events/second
- **Latency**: <50ms API response time
- **Concurrent Users**: 1,000+ WebSocket connections
- **Data Retention**: Configurable (default: 30 days)

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

MIT License - see LICENSE file

## Author

Your Name -

Project Link: [https://github.com/yourusername/eventpulse-analytics](https://github.com/yourusername/eventpulse-analytics)

## Acknowledgments

- FastAPI
- SQLAlchemy
- Celery
- Redis
- PostgreSQL
