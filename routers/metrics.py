from fastapi import APIRouter, status
from pydantic import BaseModel, Field
import time
from typing import Dict, Any

# NEW: Import shared state variables
from shared_state import GLOBAL_COUNTERS, MODEL_ARTIFACT

# --- Pydantic Models ---

class AppMetrics(BaseModel):
    """Schema for application-level metrics."""
    sync_requests: int = Field(description="Total count of synchronous recommendation requests.")
    async_jobs_submitted: int = Field(description="Total count of asynchronous jobs submitted.")
    async_jobs_completed: int = Field(description="Total count of asynchronous jobs successfully completed.")
    async_jobs_failed: int = Field(description="Total count of asynchronous jobs that failed.")
    status_checks: int = Field(description="Total number of times job status was checked.")

class ModelMetadata(BaseModel):
    """Schema for exposing information about the loaded ML model."""
    version: str = Field(description="The loaded model version.")
    loaded_at_timestamp: int = Field(description="Unix timestamp when the model was loaded.")
    uptime_seconds: float = Field(description="Time elapsed since the model was loaded.")
    is_ready: bool = Field(description="True if the model artifact is fully loaded.")
    
class MetricsResponse(BaseModel):
    """Combined schema for all monitoring endpoints."""
    app_metrics: AppMetrics
    model_info: ModelMetadata

# --- Router Initialization ---

router = APIRouter()

# --- API Endpoints ---

@router.get(
    "/metrics",
    response_model=MetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get application and model monitoring metrics."
)
def get_metrics():
    """
    Provides a snapshot of operational metrics and details about the loaded 
    Machine Learning model artifact.
    """
    
    # 1. Prepare Model Metadata
    is_model_ready = bool(MODEL_ARTIFACT)
    loaded_at = MODEL_ARTIFACT.get("loaded_at", 0)
    uptime = time.time() - loaded_at if loaded_at else 0
    
    model_data = ModelMetadata(
        version=MODEL_ARTIFACT.get("version", "N/A"),
        loaded_at_timestamp=int(loaded_at),
        uptime_seconds=round(uptime, 2),
        is_ready=is_model_ready
    )
    
    # 2. Prepare Application Counters
    app_data = AppMetrics(
        sync_requests=GLOBAL_COUNTERS["sync_requests"],
        async_jobs_submitted=GLOBAL_COUNTERS["async_submissions"], # NOTE: Corrected key access from "async_jobs_submitted" to "async_submissions" based on shared_state.py convention
        async_jobs_completed=GLOBAL_COUNTERS["async_completions"],
        async_jobs_failed=GLOBAL_COUNTERS["async_failures"],
        status_checks=GLOBAL_COUNTERS["status_checks"],
    )

    # 3. Return Combined Response
    return MetricsResponse(
        app_metrics=app_data,
        model_info=model_data
    )
