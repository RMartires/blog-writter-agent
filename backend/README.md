# Backend API Server

FastAPI backend server for the AI Blog Writer application.

## Setup

1. Install dependencies from the project root:
```bash
cd ..
pip install -r requirements.txt
```

2. Set up environment variables (create `.env` file in root directory):
```
OPENROUTER_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here
MONGO_DB_URI=mongodb://localhost:27017/
MONGO_DB_NAME=blog_researcher
```

## Running the Server

From the `backend/` directory:
```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The server will start on `http://localhost:8000`

## API Endpoints

### POST `/generate-plan/{session_id}`

Create a job to generate a blog plan based on a keyword/topic. Returns immediately with a job_id. The plan generation happens asynchronously in the background.

**Path Parameters:**
- `session_id` (string): Unique identifier for request tracking/logging

**Request Body:**
```json
{
  "keyword": "future of remote work trends"
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Job created successfully. Use GET /plan/{job_id} to check status."
}
```

**Error Responses:**
- `400`: Bad request (missing/invalid keyword)
- `500`: Server error (API key missing, database connection failed)

### GET `/plan/{job_id}`

Get the status and result of a plan generation job.

**Path Parameters:**
- `job_id` (string): Job identifier returned from POST /generate-plan/{session_id}

**Response (Processing):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "keyword": "future of remote work trends",
  "created_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-01T12:00:00",
  "plan": null,
  "error": null
}
```

**Response (Completed):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "keyword": "future of remote work trends",
  "created_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-01T12:05:30",
  "plan": {
    "title": "Blog Post Title",
    "intro": "Introduction description",
    "intro_length_guidance": "moderate",
    "sections": [
      {
        "heading": "Section Heading",
        "description": "Section description",
        "subsections": [
          {
            "heading": "Subsection Heading",
            "description": "Subsection description"
          }
        ]
      }
    ]
  },
  "error": null
}
```

**Response (Failed):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "keyword": "future of remote work trends",
  "created_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-01T12:02:15",
  "plan": null,
  "error": "Error message here"
}
```

**Error Responses:**
- `404`: Job not found
- `500`: Database connection failed

### GET `/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Architecture

The API uses an asynchronous job queue pattern:

1. **POST `/generate-plan/{session_id}`** - Creates a job and returns immediately
2. **Background Worker** - Processes jobs asynchronously (polling every 5 seconds)
3. **GET `/plan/{job_id}`** - Client polls this endpoint to check job status

### Job Status Flow

1. `processing` - Job created, waiting to be processed or currently being processed
2. `completed` - Plan generated successfully, available in response
3. `failed` - Error occurred, error message in response

### Background Worker

The background worker automatically starts when the server starts. It:
- Polls MongoDB for jobs with status "processing"
- Processes jobs sequentially (research → RAG → plan generation)
- Updates job status to "completed" or "failed"
- Runs continuously until server shutdown

## Development

The server integrates with the existing agent modules:
- `ResearchAgent`: Performs web research using Tavily API
- `RAGManager`: Builds knowledge base from research data
- `PlannerAgent`: Generates structured blog plan

All agents use configuration from `config.py` in the parent directory.

### MongoDB Collections

- `plan_generation_jobs`: Stores job status and results
- `articles`: Existing collection for article storage

