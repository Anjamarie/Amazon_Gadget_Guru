from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, status
from pydantic import BaseModel, Field, field_validator
from typing import List, Any, Dict
import asyncio
import time
import uuid
import re
import logging 
from main import MODEL_ARTIFACT, APIError, GLOBAL_COUNTERS # Added GLOBAL_COUNTERS import

# Initialize logger for this module, which will output logs based on main.py's configuration
logger = logging.getLogger(__name__) 

# Redefine APIError locally to ensure router is self-contained (as per file constraints)
class APIError(Exception):
    def __init__(self, name: str, status_code: int, detail: str):
        self.name = name
        self.status_code = status_code
        self.detail = detail

# Initialize the APIRouter for all recommendation-related endpoints
router = APIRouter()

# --- Configuration & Mock Data ---

VALID_USER_IDS = {
    "USER-A100F951F8W1K",
    "USER-B201G842E9X2L",
    "USER-C302H733D0Y3M",
    "USER-D403I624C1Z4N"
}

# The dictionary storing background job results
BACKGROUND_TASK_RESULTS: Dict[str, Any] = {}


# --- Pydantic Models (Unchanged) ---
class RecommendationRequest(BaseModel):
    user_id: str = Field(..., pattern=r"^USER-[a-zA-Z0-9]+$")
    num_recommendations: int = Field(5, ge=1, le=20)

    @field_validator('num_recommendations')
    @classmethod
    def must_be_odd(cls, value: int) -> int:
        if value % 2 == 0:
            raise ValueError("Number of recommendations must be an odd number.")
        return value

class RecommendedItem(BaseModel):
    product_id: str = Field(...)
    score: float = Field(...)
    title: str = Field(...)

class RecommendationResponse(BaseModel):
    user_id: str = Field(...)
    recommendations: List[RecommendedItem] = Field(...)
    model_version: str = Field("v2.3")
    processing_mode: str = Field(...)

class SubmissionResponse(BaseModel):
    user_id: str
    status: str
    job_id: str
    message: str


# --- Dependency Functions ---

def validate_user_and_get_request(request_body: RecommendationRequest) -> RecommendationRequest:
    """Reusable dependency. If validation fails, it raises the custom APIError."""
    if request_body.user_id not in VALID_USER_IDS:
        raise APIError(
            name="USER_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User ID '{request_body.user_id}' not found. Cannot generate recommendations."
        )
    return request_body
    
def get_cached_model() -> Dict[str, Any]:
    """
    FastAPI Dependency that checks if the model artifact is loaded and returns it.
    This simulates injecting the cached model object into the request path.
    """
    if not MODEL_ARTIFACT or 'version' not in MODEL_ARTIFACT:
        # If the model isn't loaded (e.g., startup failed), raise 503
        raise APIError(
            name="MODEL_NOT_READY",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The ML model is not yet loaded or failed to initialize during startup."
        )
    return MODEL_ARTIFACT


# --- Core Logic & Workers (Unchanged) ---

async def generate_mock_recommendations(user_id: str, num: int) -> List[RecommendedItem]:
    """Generates mock data and simulates a 2-second non-blocking delay."""
    await asyncio.sleep(2) 
    mock_items = []
    base_id = int(hash(user_id) % 1000)
    
    for i in range(num):
        mock_items.append(
            RecommendedItem(
                product_id=f"B00{base_id + i}",
                score=round(0.95 - (i * 0.05), 3),
                title=f"Mock Product {base_id + i}: High Performance Item"
            )
        )
    return mock_items

def background_worker(user_id: str, num_recommendations: int, job_id: str):
    """
    Simulates a long-running, blocking task that saves results for later retrieval.
    Includes structured logging for MLOps observability.
    """
    start_time = time.time()
    # Define a base dictionary for structured logging (metadata for observability)
    log_context = {'job_id': job_id, 'user_id': user_id, 'task_type': 'async_recommendations'}

    # 1. Log Job Start
    logger.info("Starting background recommendation job.", extra=log_context)
    
    try:
        # Simulation of blocking ML model inference/processing
        time.sleep(1.5) 
        
        mock_items = []
        base_id = int(hash(user_id) % 1000)
        for i in range(num_recommendations):
            mock_items.append(
                RecommendedItem(
                    product_id=f"D00{base_id + i}",
                    score=round(0.85 - (i * 0.05), 3),
                    title=f"Mock Product {base_id + i}: Background Processed Item"
                )
            )
        
        # Calculate latency
        latency = round(time.time() - start_time, 3)
        
        # Store result
        BACKGROUND_TASK_RESULTS[job_id] = {
            "user_id": user_id,
            "recommendations": mock_items,
            "status": "COMPLETED"
        }
        
        # 2. Log Job Success with key performance indicators (KPIs)
        success_context = {
            **log_context, 
            'status': 'SUCCESS', 
            'result_count': len(mock_items), 
            'latency_seconds': latency
        }
        logger.info("Background job completed successfully.", extra=success_context)
        
    except Exception as e:
        # 3. Log Job Failure with detailed error information
        failure_context = {
            **log_context, 
            'status': 'FAILED', 
            'error_type': type(e).__name__, 
            'error_message': str(e)
        }
        # Use logger.error and exc_info=True to include the traceback in the logs
        logger.error(f"Background job failed: {str(e)}", exc_info=True, extra=failure_context)
        
        BACKGROUND_TASK_RESULTS[job_id] = {"status": "FAILED", "error": str(e)}


# --- Router Endpoints (Updated /sync) ---

@router.post(
    "/sync", 
    response_model=RecommendationResponse,
    summary="Synchronous (200 OK) recommendation with performance simulation."
)
async def get_sync_recommendations(
    request_body: RecommendationRequest = Depends(validate_user_and_get_request),
    cached_model: Dict[str, Any] = Depends(get_cached_model) 
):
    """
    Generates recommendations synchronously. The cached model is injected 
    via a dependency, confirming the model artifact is loaded before inference 
    and ensuring the correct model version is used in the response.
    """
    # --- METRICS UPDATE ---
    GLOBAL_COUNTERS['total_sync_requests'] += 1
    logger.info("Synchronous request processed.", extra={'user_id': request_body.user_id, 'mode': 'sync'})
    # ----------------------
    
    user_id = request_body.user_id
    num_recommendations = request_body.num_recommendations
    model_version = cached_model['version'] # Get version from the loaded artifact
    
    recommended_items = await generate_mock_recommendations(user_id, num_recommendations)

    return RecommendationResponse(
        user_id=user_id,
        recommendations=recommended_items,
        processing_mode="sync",
        model_version=model_version
    )


@router.post(
    "/submit", 
    response_model=SubmissionResponse,
    status_code=202,
    summary="Asynchronous (202 Accepted) recommendation using BackgroundTasks."
)
def submit_recommendation_job(
    request_body: RecommendationRequest = Depends(validate_user_and_get_request),
    background_tasks: BackgroundTasks = None
):
    """Submits a recommendation job to be processed in the background."""
    user_id = request_body.user_id
    
    job_id = str(uuid.uuid4())
    
    background_tasks.add_task(background_worker, user_id, request_body.num_recommendations, job_id)
    
    BACKGROUND_TASK_RESULTS[job_id] = {"status": "PENDING", "user_id": user_id}

    # --- METRICS UPDATE ---
    GLOBAL_COUNTERS['total_submit_requests'] += 1
    logger.info("Background job submitted.", extra={'user_id': user_id, 'job_id': job_id, 'mode': 'async'})
    # ----------------------

    return SubmissionResponse(
        user_id=user_id,
        status="ACCEPTED",
        job_id=job_id,
        message=f"Job submitted. Check status at /v1/recommendations/status/{job_id} later."
    )


@router.get(
    "/status/{job_id}", 
    summary="Check status and retrieve results of a background job."
)
def get_job_status(job_id: str):
    """Allows the client to poll the server for the result of a background job."""
    
    if job_id not in BACKGROUND_TASK_RESULTS:
        raise HTTPException(status_code=404, detail=f"Job ID '{job_id}' not found.")
        
    job_info = BACKGROUND_TASK_RESULTS[job_id]
    
    if job_info["status"] == "COMPLETED":
        return RecommendationResponse(
            user_id=job_info["user_id"],
            recommendations=job_info["recommendations"],
            processing_mode="async",
            model_version="v2.3"
        )
        
    return {"job_id": job_id, "status": job_info["status"], "message": "Processing is still underway."}
