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

### POST `/generate-plan/{uuid}`

Generate a blog plan based on a keyword/topic.

**Path Parameters:**
- `uuid` (string): Unique identifier for request tracking/logging

**Request Body:**
```json
{
  "keyword": "future of remote work trends"
}
```

**Response:**
```json
{
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
}
```

**Error Responses:**
- `400`: Bad request (missing/invalid keyword)
- `500`: Server error (API key missing, research failed, plan generation failed)

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

## Development

The server integrates with the existing agent modules:
- `ResearchAgent`: Performs web research using Tavily API
- `RAGManager`: Builds knowledge base from research data
- `PlannerAgent`: Generates structured blog plan

All agents use configuration from `config.py` in the parent directory.

