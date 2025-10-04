from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, field_validator
from typing import List, Any, Dict
import asyncio
import time
import uuid
import re

# --- Configuration & Mock Data ---

# Define a set of "valid" user IDs for simulating a database lookup.
# NOTE: The actual validation now also requires the ID to match the 'USER-' prefix defined in the model.
VALID_USER_IDS = {
    "USER-A100F951F8W1K", # Updated to match new format
    "USER-B201G842E9X2L", # Updated to match new format
    "USER-C302H733D0Y3M", # Updated to match new format
    "USER-D403I624C1Z4N"  # Updated to match new format
}

# In a real application, this would be a cache or a database table
BACKGROUND_TASK_RESULTS: Dict[str, Any] = {}


# --- Pydantic Models with Enhanced Validation ---

# Represents the data expected in the POST request body
class RecommendationRequest(BaseModel):
    # Rule 1: User ID must be a string and MUST match the regex pattern.
    # We enforce that the user ID must start with "USER-" followed by alphanumeric characters.
    user_id: str = Field(
        ...,
        description="The ID of the user (must start with 'USER-').",
        pattern=r"^USER-[a-zA-Z0-9]+$"
    )
    
    # Rule 2: Number of recommendations must be between 1 and 20 (inclusive).
    num_recommendations: int = Field(
        5,
        description="The desired number of recommendations (must be between 1 and 20, and must be odd).",
        ge=1,
        le=20
    )

    # Rule 3: Custom Pydantic validator to ensure the number is odd.
    @field_validator('num_recommendations')
    @classmethod
    def must_be_odd(cls, value: int) -> int:
        """Custom validation to ensure num_recommendations is an odd number."""
        if value % 2 == 0:
            raise ValueError("Number of recommendations must be an odd number (e.g., 1, 3, 5, 7...).")
        return value

# Represents a single product recommendation item
class RecommendedItem(BaseModel):
    product_id: str = Field(..., description="The unique identifier of the recommended product.")
    score: float = Field(..., description="The confidence score for the recommendation.")
    title: str = Field(..., description="Mock title for the product.")

# Represents the full response structure (Used for 200 OK sync response)
class RecommendationResponse(BaseModel):
    user_id: str = Field(..., description="The user ID the recommendations were generated for.")
    recommendations: List[RecommendedItem] = Field(..., description="A list of recommended products.")
    model_version: str = Field("v2.3", description="The version of the recommendation engine used.")
    processing_mode: str = Field(..., description="The mode of processing (sync or async).")

# Represents the immediate response for a background task submission (Used for 202 ACCEPTED)
class SubmissionResponse(BaseModel):
    user_id: str
    status: str
    job_id: str
    message: str


# --- FastAPI App Initialization ---
app = FastAPI(title="Recommendation Service (Enhanced Validation)", version="1.0.3")


# --- Core Recommendation Logic (Asynchronous and Non-Blocking) ---

async def generate_mock_recommendations(user_id: str, num: int) -> List[RecommendedItem]:
    """Generates mock data and simulates a 2-second non-blocking delay."""
    
    print(f"--- [ASYNC] Simulating 2-second non-blocking delay for user: {user_id} ---")
    await asyncio.sleep(2) 
    print(f"--- [ASYNC] Recommendation processing complete for user: {user_id} ---")

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

# --- Background Task Worker (Synchronous and Blocking) ---

def background_worker(user_id: str, num_recommendations: int, job_id: str):
    """
    Simulates a long-running, blocking task that saves results for later retrieval.
    """
    try:
        print(f"[BACKGROUND WORKER] Starting blocking processing for Job ID: {job_id}")
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

        BACKGROUND_TASK_RESULTS[job_id] = {
            "user_id": user_id,
            "recommendations": mock_items,
            "status": "COMPLETED"
        }
        
        print(f"[BACKGROUND WORKER] Job ID {job_id} completed and results saved.")
        
    except Exception as e:
        BACKGROUND_TASK_RESULTS[job_id] = {"status": "FAILED", "error": str(e)}
        print(f"[BACKGROUND WORKER] Error processing Job ID {job_id}: {e}")

# --- API Endpoints ---

def check_user_validity(user_id: str):
    """Utility function for error handling (checking against the mock database)."""
    if user_id not in VALID_USER_IDS:
        # Note: This check only happens AFTER Pydantic validation passes.
        raise HTTPException(status_code=404, detail=f"User ID '{user_id}' not found in database or is invalid.")


@app.post(
    "/recommend/sync",
    response_model=RecommendationResponse,
    summary="Synchronous (200 OK) recommendation with performance simulation."
)
async def get_sync_recommendations(request_body: RecommendationRequest):
    """
    Generates recommendations synchronously. The client must wait for the full 2-second processing delay.
    Pydantic validation (422) happens automatically before this function runs.
    """
    user_id = request_body.user_id
    num_recommendations = request_body.num_recommendations
    
    check_user_validity(user_id)

    # Core logic runs, simulating a 2-second wait (non-blocking)
    recommended_items = await generate_mock_recommendations(user_id, num_recommendations)

    # Return the structured response after the delay
    return RecommendationResponse(
        user_id=user_id,
        recommendations=recommended_items,
        processing_mode="sync"
    )


@app.post(
    "/recommend/submit",
    response_model=SubmissionResponse,
    status_code=202, # HTTP 202 ACCEPTED status code
    summary="Asynchronous (202 Accepted) recommendation using BackgroundTasks."
)
def submit_recommendation_job(request_body: RecommendationRequest, background_tasks: BackgroundTasks):
    """
    Submits a recommendation job to be processed in the background. 
    Pydantic validation (422) happens automatically before this function runs.
    """
    user_id = request_body.user_id
    
    check_user_validity(user_id)
    
    job_id = str(uuid.uuid4())
    
    # Add the long-running worker function to the background task queue
    background_tasks.add_task(background_worker, user_id, request_body.num_recommendations, job_id)
    
    # Store initial status
    BACKGROUND_TASK_RESULTS[job_id] = {"status": "PENDING", "user_id": user_id}

    return SubmissionResponse(
        user_id=user_id,
        status="ACCEPTED",
        job_id=job_id,
        message=f"Job submitted. Check status at /recommend/status/{job_id} later."
    )


@app.get(
    "/recommend/status/{job_id}",
    summary="Check status and retrieve results of a background job."
)
def get_job_status(job_id: str):
    """Allows the client to poll the server for the result of a background job."""
    
    if job_id not in BACKGROUND_TASK_RESULTS:
        raise HTTPException(status_code=404, detail=f"Job ID '{job_id}' not found.")
        
    job_info = BACKGROUND_TASK_RESULTS[job_id]
    
    if job_info["status"] == "COMPLETED":
        # Successfully processed. Return the full recommendation data.
        return RecommendationResponse(
            user_id=job_info["user_id"],
            recommendations=job_info["recommendations"],
            processing_mode="async",
            model_version="v2.3"
        )
        
    return {"job_id": job_id, "status": job_info["status"], "message": "Processing is still underway."}

@app.get("/")
def read_root():
    return {"message": "Recommendation Service is running. Use POST /recommend/sync or /recommend/submit."}
