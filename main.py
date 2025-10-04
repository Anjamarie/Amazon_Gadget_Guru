from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
import logging
import json
import os
import sys

# Import the router and shared state components
from routers import recommendations
from shared_state import MODEL_ARTIFACT, GLOBAL_COUNTERS

# --- Logging Configuration ---

# Configure root logger to output structured JSON logs
def configure_logging():
    """Sets up basic structured logging."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Check if we are running in an environment that expects structured logs (like a deployment environment)
    # If not, use standard console logging, but keep the structure setup in place.
    if os.environ.get('LOG_FORMAT') == 'json':
        log_handler = logging.StreamHandler(sys.stdout)
        formatter = StructuredJSONFormatter()
        log_handler.setFormatter(formatter)
        logger.addHandler(log_handler)
    else:
        # Default simple format for development
        logging.basicConfig(
            level=logging.INFO,
            format='%(levelname)s: %(name)s: %(message)s'
        )

# Simple Structured JSON Formatter (simulating a complex production setup)
class StructuredJSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "pathname": record.pathname,
            "lineno": record.lineno,
            "funcName": record.funcName,
        }
        return json.dumps(log_record)

configure_logging()
logger = logging.getLogger(__name__)

# --- FastAPI App Initialization ---

app = FastAPI(
    title="Recommendation Service API",
    description="Service providing both synchronous (low-latency) and asynchronous (heavy computation) item recommendations.",
    version="1.0.0"
)

# Include the recommendation routes
app.include_router(recommendations.router, prefix="/recommendations", tags=["Recommendations"])


# --- Root and Status Endpoints ---

@app.get("/", tags=["Info"], status_code=status.HTTP_200_OK)
def root():
    """Returns basic service information."""
    logger.info("Root endpoint accessed.")
    return JSONResponse(content={
        "service": app.title,
        "version": app.version,
        "status": "Online",
        "model_loaded": MODEL_ARTIFACT["name"]
    })

@app.get("/status", tags=["Info"], status_code=status.HTTP_200_OK)
def get_service_status():
    """Returns the current status of the service, including model and job counters."""
    logger.info("Status endpoint accessed.")
    
    # Safely combine global data for reporting
    status_report = {
        "service_health": "Operational",
        "model_artifact": MODEL_ARTIFACT,
        "global_counters": GLOBAL_COUNTERS,
    }
    
    return JSONResponse(content=status_report)

# --- Startup and Shutdown Events ---

@app.on_event("startup")
async def startup_event():
    """Logs model and initial state on startup."""
    logger.info("--- Application Startup ---")
    logger.info(f"Model Artifact loaded: {MODEL_ARTIFACT['name']}")
    logger.info("Application is ready to accept connections.")

@app.on_event("shutdown")
def shutdown_event():
    """Logs a summary of activity before shutdown."""
    logger.info("--- Application Shutdown ---")
    logger.info(f"Total Sync Calls: {GLOBAL_COUNTERS['sync_calls']}")
    logger.info(f"Total Async Submissions: {GLOBAL_COUNTERS['async_submissions']}")
    logger.info(f"Total Async Completions: {GLOBAL_COUNTERS['async_completions']}")
    logger.info("Application has shut down.")
