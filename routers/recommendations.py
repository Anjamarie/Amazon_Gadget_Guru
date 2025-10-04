from fastapi import APIRouter, status, BackgroundTasks, HTTPException
from pydantic import BaseModel
import logging
import random
import time

# Import shared state and dependencies from the centralized file
from shared_state import (
    get_recommendations_sync, 
    process_async_recommendation_task, 
    get_job_status, # <--- Function to check job status
    get_job_results, # <--- Function to retrieve job results
    GLOBAL_COUNTERS
)

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Pydantic Models ---

class RecommendationRequest(BaseModel):
    """Schema for the input request."""
    user_id: str
    num_items: int

class SyncResponse(BaseModel):
    """Schema for the synchronous response."""
    user_id: str
    recommendations: list[str]
    model_version: str

class AsyncSubmitResponse(BaseModel):
    """Schema returned immediately upon submitting an asynchronous job."""
    user_id: str
    job_id: str
    status: str
    message: str

class AsyncStatusResponse(BaseModel):
    """Schema for checking the status of an asynchronous job."""
    job_id: str
    status: str # e.g., SUBMITTED, IN_PROGRESS, COMPLETE, FAILED
    message: str
    user_id: str | None = None
    progress: int = 0 # Percentage completion (0 to 100)

class AsyncResultResponse(BaseModel):
    """Schema for the final asynchronous recommendation result."""
    job_id: str
    status: str
    user_id: str
    recommendations: list[str]
    model_version: str

# --- Synchronous Endpoint (POST Request - Now at /recommendations/post_sync) ---

@router.post("/post_sync", response_model=SyncResponse, status_code=status.HTTP_200_OK)
def post_sync_recommendations(request: RecommendationRequest):
    """
    Synchronous endpoint for real-time recommendations (fast response).
    Accepts data via a JSON request body at the base /recommendations/post_sync path.
    """
    logger.info(f"Handling synchronous POST request for user: {request.user_id}")
    
    # Update counter
    GLOBAL_COUNTERS["sync_calls"] += 1 

    # Call the synchronous model logic defined in shared_state
    results = get_recommendations_sync(request.user_id, request.num_items)
    
    # Extract model version from one of the simulated item strings for the response
    model_version = "unknown"
    if results and len(results) > 0 and '_v' in results[0]:
        try:
            # Assumes format: item_XYZ_v1.0.0-user_ABC
            model_version = results[0].split('_v')[1].split('-')[0]
        except IndexError:
            pass # Keep as 'unknown' if splitting fails

    return SyncResponse(
        user_id=request.user_id,
        recommendations=results,
        model_version=model_version
    )

# --- Synchronous Endpoint (GET Request - expects Path and Query parameters) ---

# This path remains /sync/{user_id}
@router.get("/sync/{user_id}", response_model=SyncResponse, status_code=status.HTTP_200_OK)
def get_sync_recommendations(user_id: str, num_items: int = 5):
    """
    Synchronous endpoint for real-time recommendations (fast response).
    Accepts user_id via URL path and num_items via query parameter.
    """
    logger.info(f"Handling synchronous GET request for user: {user_id}")
    
    # Update counter
    GLOBAL_COUNTERS["sync_calls"] += 1 

    # Call the synchronous model logic defined in shared_state
    results = get_recommendations_sync(user_id, num_items)
    
    # Extract model version from one of the simulated item strings for the response
    model_version = "unknown"
    if results and len(results) > 0 and '_v' in results[0]:
        try:
            # Assumes format: item_XYZ_v1.0.0-user_ABC
            model_version = results[0].split('_v')[1].split('-')[0]
        except IndexError:
            pass # Keep as 'unknown' if splitting fails

    return SyncResponse(
        user_id=user_id,
        recommendations=results,
        model_version=model_version
    )


# --- Asynchronous Endpoints ---

@router.post("/async/submit", response_model=AsyncSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_async_recommendations(request: RecommendationRequest, background_tasks: BackgroundTasks):
    """
    Asynchronous endpoint to submit a long-running recommendation job.
    Returns immediately (HTTP 202 Accepted) and processes the task in the background 
    using FastAPI's BackgroundTasks feature.
    """
    # Generate a unique job ID
    job_id = f"job-{random.randint(10000, 99999)}-{time.time_ns()}"
    
    logger.info(f"Submitting async job {job_id} for user: {request.user_id}")
    
    # Add the heavy processing function as a non-blocking background task
    background_tasks.add_task(process_async_recommendation_task, 
                              job_id=job_id, # Pass job_id to the processor
                              user_id=request.user_id, 
                              data=request.model_dump())
    
    # Update counter
    GLOBAL_COUNTERS["async_submissions"] += 1
    
    return AsyncSubmitResponse(
        user_id=request.user_id,
        job_id=job_id,
        status="SUBMITTED",
        message=f"Recommendation job {job_id} submitted. Check status at /async/status/{job_id}"
    )

@router.get("/async/status/{job_id}", response_model=AsyncStatusResponse, status_code=status.HTTP_200_OK)
def get_async_job_status(job_id: str):
    """
    Retrieves the current status and progress of a submitted asynchronous job.
    """
    status_data = get_job_status(job_id)

    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job ID '{job_id}' not found."
        )

    return AsyncStatusResponse(**status_data)

@router.get("/async/results/{job_id}", response_model=AsyncResultResponse, status_code=status.HTTP_200_OK)
def get_async_job_results(job_id: str):
    """
    Retrieves the final results of a completed asynchronous job.
    """
    result_data = get_job_results(job_id)

    if not result_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job ID '{job_id}' not found."
        )

    status_code = result_data.get("status")
    
    if status_code in ["SUBMITTED", "IN_PROGRESS"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job ID '{job_id}' is still {status_code}. Check status first."
        )
    
    if status_code == "FAILED":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Job ID '{job_id}' failed: {result_data.get('message', 'No error message provided.')}"
        )

    # For 'COMPLETE' status
    return AsyncResultResponse(
        job_id=job_id,
        status=status_code,
        user_id=result_data.get("user_id"),
        recommendations=result_data.get("recommendations", []),
        model_version=result_data.get("model_version", "unknown")
    )
