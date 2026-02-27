# Production-Ready Machine Learning Engineer Portfolio
## Amazon Electronics Recommendation Engine
### Project Overview
This project demonstrates the core technical capability required for personalization systems at scale: building, deploying, and monitoring a low-latency recommendation engine.

The primary goal was to take the Matrix Factorization (SVD) model from concept to a production-ready microservice to prove MLOps proficiency.

***

### The "Why" 
**Problem:** Recommendation models are often stuck in notebooks.


**Solution:** Built a resilient microservice that handles matrix factorization at scale, utilizing BackgroundTasks to prevent API blocking during high-volume inference.
***

### Methodology and Core Algorithms

| Component | Technology | Concept |
| :--- | :--- | :--- |
| **Data Filtering** | `Pandas`, `NumPy` | Aggressively reduced data sparsity by filtering out users and items with fewer than 5 ratings/interactions, ensuring the model trains on meaningful user behavior. |
| **Modeling Core** | Singular Value Decomposition (SVD), `surprise` Library | Implemented SVD to perform Matrix Factorization, learning user and item latent features to drive personalized predictions. |
| **Model Packaging** | Joblib Serialization | Serialized the final trained model (recommender_model.joblib) for efficient loading into the production API, preventing the need for retraining on startup. |
| **API Architecture** | FastAPI, Routers, BackgroundTasks| Designed a modular, scalable API structure capable of handling both synchronous (low-latency) and asynchronous (long-running) recommendation requests. |

***

### MLOps 
| Feature | Technology | Benefit |
| :--- | :--- | :--- |
| **Liveness Probes** | `/health/liveness` | Allows Kubernetes/Cloud Run to restart the container if it freezes. |
| **Modeling Caching** | Lifespan Events | Prevents 500ms+ overhead by loading the .joblib into RAM exactly once. |
| **Metrics** | `/v1/metrics` | Enables real-time monitoring of P99 latency and error rates. |


***


## Key Performance Metrics (SVD Model)

| Metric | Value | Interpretation |
| :--- | :--- | :--- |
| **Mean RMSE** | 0.89 | Predicted ratings are off by < 0.9 points on a 5-point scale, indicating high accuracy. |
| **Latency (P99)** | ~980ms | Provides near-real-time responses for synchronous requests (under 1 second). |
| **Async Reliability** | 100% | BackgroundTask mechanism successfully manages job state and retrieval. |

## Repository Structure

* **main.py**: Application entry point, lifespan management, and dependency injection.
* **routers/**: Modular directory containing endpoint logic and shared state modules.
* **recommender_model.joblib**: Serialized ML model artifact ready for production inference.
* **assets/**: Visualizations, architecture diagrams, and static assets for documentation.


***


### Conclusion & Future Work

This project successfully transitioned a Matrix Factorization research concept into a resilient, asynchronous microservice. The system achieves high predictive accuracy (0.89 RMSE) while maintaining the low latency required for production user experiences. The limitations include system struggles to make recommendations for users who have zero history, the current model is static and would need to be re-trained to capture changes, and there is hardware constraints and the SVD matrix would need to be transitioned to a GPU-accelerated training or a distributed system. 

---
> **Note:** View the complete analysis and model training code in the [ML-core.ipynb](./ML-core.ipynb) file.
