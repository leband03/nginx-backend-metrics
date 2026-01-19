import os
import time
import logging
from fastapi import FastAPI, Response, Request
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

APP_NAME = os.getenv("APP_NAME", "demo-app")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
GIT_COMMIT = os.getenv("GIT_COMMIT", "dev")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(APP_NAME)

app = FastAPI(title=APP_NAME)

# --- Prometheus metrics ---
REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"]
)

LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency (seconds)",
    ["method", "path"]
)

IN_FLIGHT = Gauge(
    "http_in_flight_requests",
    "In-flight HTTP requests"
)

BUILD_INFO = Gauge(
    "build_info",
    "Build info",
    ["app", "version", "commit"]
)
BUILD_INFO.labels(app=APP_NAME, version=APP_VERSION, commit=GIT_COMMIT).set(1)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method

    # не считаем метрики для /metrics чтобы не зашумлять
    if path == "/metrics":
        return await call_next(request)

    IN_FLIGHT.inc()
    start = time.time()
    try:
        response = await call_next(request)
        status = str(response.status_code)
        return response
    except Exception:
        status = "500"
        raise
    finally:
        duration = time.time() - start
        IN_FLIGHT.dec()
        LATENCY.labels(method=method, path=path).observe(duration)
        REQUESTS.labels(method=method, path=path, status=status).inc()

        logger.info("request method=%s path=%s status=%s duration=%.4f",
                    method, path, status, duration)


@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION, "commit": GIT_COMMIT}


@app.get("/api/hello")
def hello():
    return {"message": "hello from backend", "app": APP_NAME}


@app.get("/metrics")
def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@app.get("/")
def root():
    # корень оставим для примера (обычно его отдаёт nginx)
    return {"message": "root from backend (usually behind nginx)"}
