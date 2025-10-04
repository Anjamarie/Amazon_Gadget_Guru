from fastapi import APIRouter, status
from pydantic import BaseModel, Field
import time

# Import shared state variables
from shared_state import MODEL_ARTIFACT, GLOBAL_COUNTERS

# --- Pydantic Model ---

class HealthResponse(BaseModel):
    """Schema for the basic health check response."""
    status: str = Field(description="The overall service status (e.g., 'OK', 'Degraded').")
    app_uptime_seconds: float = Field(description="Total time the application has been running.")
    model_ready: bool = Field(description="True if the ML model artifact is loaded and ready.")
    model_version: str = Field(description="The loaded model version.")

# --- Router Initialization ---

router = APIRouter()

# --- API Endpoints ---

@router.get(
    "/status",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Basic health and readiness check."
)
def get_status():
    """
    Returns the application's current health status and basic uptime information.
    """
    
    is_model_ready = MODEL_ARTIFACT.get("is_ready", False)
    app_startup_time = GLOBAL_COUNTERS.get("startup_time", time.time())
    
    uptime = time.time() - app_startup_time
    
    # Determine overall status
    if is_model_ready:
        service_status = "OK"
    else:
        service_status = "Degraded (Model Loading)"
        
    return HealthResponse(
        status=service_status,
        app_uptime_seconds=round(uptime, 2),
        model_ready=is_model_ready,
        model_version=MODEL_ARTIFACT.get("version", "N/A - Loading")
    )
