from fastapi import APIRouter, status, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any
import time
import logging

# Import necessary globals from main and the recommendations router
from main import MODEL_ARTIFACT, GLOBAL_COUNTERS, APIError
from routers.recommendations import BACKGROUND_TASK_RESULTS

logger = logging.getLogger(__name__) 

# Initialize the APIRouter
router = APIRouter()

# --- Pydantic Models for Metrics Output ---

class SystemMetrics(BaseModel):
    uptime_seconds: float = Field(..., description="Time since the application started in seconds.")
    
class ModelMetrics(BaseModel):
    version: str = Field(..., description="Version of the ML model currently loaded.")
    load_timestamp: float = Field(..., description="UNIX timestamp when the model was loaded (via lifespan event).")
    time_since_load_seconds: float = Field(..., description="Time elapsed since the model was loaded.")
    
class RequestMetrics(BaseModel):
    total_sync_requests: int = Field(..., description="Total count of synchronous recommendation requests.")
    total_submit_requests: int = Field(..., description="Total count of background job submissions.")

class JobMetrics(BaseModel):
    total_jobs_submitted: int = Field(..., description="Total number of jobs ever submitted (matches total_submit_requests).")
    jobs_pending: int = Field(..., description="Number of jobs currently in PENDING status.")
    jobs_completed: int = Field(..., description="Total number of jobs successfully COMPLETED.")
    jobs_failed: int = Field(..., description="Total number of jobs that FAILED.")
    
class MetricsResponse(BaseModel):
    system: SystemMetrics
    model: ModelMetrics
    requests: RequestMetrics
    jobs: JobMetrics


# --- Helper Dependency ---

def get_app_start_time() -> float:
    """A mock dependency to simulate getting the app start time."""
    # Mocking 100 seconds of uptime to demonstrate the calculation
    return time.time() - 100 

# --- Endpoint ---

@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Operational Metrics: Provides model, request, and job status observability."
)
def get_operational_metrics(app_start_time: float = Depends(get_app_start_time)):
    """
    Calculates and returns key performance indicators and operational metrics
    for monitoring the recommendation service.
    """
    
    # --- 1. Validate Model Readiness ---
    if not MODEL_ARTIFACT or 'loaded_at' not in MODEL_ARTIFACT:
        raise APIError(
            name="MODEL_METRICS_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model metrics cannot be generated because the ML model artifact is not loaded."
        )

    current_time = time.time()
    
    # --- 2. Calculate Job Metrics ---
    jobs_pending = 0
    jobs_completed = 0
    jobs_failed = 0
    
    # Iterate through the results dictionary to aggregate statuses
    for job_id, result in BACKGROUND_TASK_RESULTS.items():
        status = result.get('status')
        if status == "PENDING":
            jobs_pending += 1
        elif status == "COMPLETED":
            jobs_completed += 1
        elif status == "FAILED":
            jobs_failed += 1

    # --- 3. Assemble Response ---
    
    metrics = MetricsResponse(
        system=SystemMetrics(
            uptime_seconds=round(current_time - app_start_time, 2)
        ),
        model=ModelMetrics(
            version=MODEL_ARTIFACT.get('version', 'N/A'),
            load_timestamp=MODEL_ARTIFACT['loaded_at'],
            time_since_load_seconds=round(current_time - MODEL_ARTIFACT['loaded_at'], 2)
        ),
        requests=RequestMetrics(
            total_sync_requests=GLOBAL_COUNTERS.get('total_sync_requests', 0),
            total_submit_requests=GLOBAL_COUNTERS.get('total_submit_requests', 0)
        ),
        jobs=JobMetrics(
            total_jobs_submitted=GLOBAL_COUNTERS.get('total_submit_requests', 0), 
            jobs_pending=jobs_pending,
            jobs_completed=jobs_completed,
            jobs_failed=jobs_failed
        )
    )
    
    logger.info("Metrics endpoint accessed successfully.")
    return metrics
