import time
import random
import logging

logger = logging.getLogger(__name__)

# --- Global State Stores ---
# These simulate a key-value store (like Redis or a database) used for job tracking
job_statuses = {}
job_results = {}

# Mock Model Artifact (e.g., loaded weights, config)
MODEL_ARTIFACT = {
    "name": "Collaborative_Filter_v1.2.3",
    "version": "v1.2.3",
    "loaded_at": time.time()
}

# Global counters for service monitoring
GLOBAL_COUNTERS = {
    "sync_calls": 0,
    "async_submissions": 0,
    "async_completions": 0
}

# --- Core Logic Functions ---

def get_recommendations_sync(user_id: str, num_items: int) -> list[str]:
    """
    Simulates a fast, synchronous recommendation call.
    """
    # Simulate lookup time
    time.sleep(0.01) 
    
    version = MODEL_ARTIFACT["version"]
    
    # Generate mock results
    results = [
        f"item_{random.randint(1000, 9999)}_v{version}-user_{user_id}" 
        for _ in range(num_items)
    ]
    return results

def process_async_recommendation_task(job_id: str, user_id: str, data: dict):
    """
    Simulates a long-running, CPU-intensive recommendation calculation 
    that runs in a background thread.
    """
    logger.info(f"Async job {job_id} started for user {user_id}. Simulating 5 seconds of work.")
    
    # --- SIMULATED FAILURE POINT ---
    # If the user_id starts with "FAIL", simulate a 50% chance of failure
    if user_id.startswith("FAIL") and random.random() < 0.5:
        job_statuses[job_id]["status"] = "FAILED"
        job_statuses[job_id]["message"] = "Simulated internal model corruption error during processing."
        job_results[job_id] = job_statuses[job_id] # Store failure status in results
        logger.error(f"Async job {job_id} FAILED during processing for user {user_id}.")
        return
    # --- END SIMULATED FAILURE POINT ---

    try:
        # Initial status setup
        job_statuses[job_id] = {
            "job_id": job_id,
            "status": "IN_PROGRESS",
            "message": "Processing recommendation batch...",
            "user_id": user_id,
            "progress": 0
        }
        
        # Simulating work in 5 chunks
        num_items = data.get("num_items", 5)
        version = MODEL_ARTIFACT["version"]
        recommendations = []
        
        for i in range(1, 6):
            time.sleep(1) # Simulate 1 second of heavy computation
            progress = i * 20
            job_statuses[job_id]["progress"] = progress
            logger.debug(f"Async job {job_id} progress: {progress}%")

        # After work is done, generate final results
        recommendations = [
            f"item_{random.randint(20000, 29999)}_v{version}-user_{user_id}-long_run"
            for _ in range(num_items)
        ]
        
        # Final status update
        job_statuses[job_id]["status"] = "COMPLETE"
        job_statuses[job_id]["message"] = "Job complete."
        job_statuses[job_id]["progress"] = 100
        
        # Store results in job_results cache
        job_results[job_id] = {
            **job_statuses[job_id], # Include status metadata
            "recommendations": recommendations,
            "model_version": version
        }
        
        GLOBAL_COUNTERS["async_completions"] += 1
        logger.info(f"Async job {job_id} COMPLETED successfully.")

    except Exception as e:
        logger.error(f"Async job {job_id} encountered an unexpected error: {e}", exc_info=True)
        # Handle unexpected exceptions
        job_statuses[job_id]["status"] = "FAILED"
        job_statuses[job_id]["message"] = f"Unexpected processing error: {str(e)}"
        job_results[job_id] = job_statuses[job_id]

# --- Global State Accessors ---

def get_job_status(job_id: str):
    """Retrieves current status from the temporary job_statuses store."""
    return job_statuses.get(job_id)

def get_job_results(job_id: str):
    """Retrieves final result data from the job_results store."""
    return job_results.get(job_id)
