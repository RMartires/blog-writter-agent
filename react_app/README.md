# AI Blog Writer - Frontend

Next.js frontend application for the AI Blog Writer.

## Getting Started

First, install the dependencies:

```bash
npm install
```

Create a `.env.local` file in the root directory:

```bash
NEXT_PUBLIC_API_HOST=http://localhost:8000
```

Then, run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Features

- Modern dark theme UI
- Quick Draft and Detailed Outline modes
- Topic/keyword input for blog generation
- Async job-based API integration
- Real-time polling for job status
- Loading screen with animated spinner
- Responsive design

## API Integration

The frontend integrates with the backend API:

1. **POST `/generate-plan/{session_id}`** - Creates a job and returns job_id
2. **GET `/plan/{job_id}`** - Polls job status every 2 seconds until completed

The app automatically:
- Shows a loading screen while the job is processing
- Polls the status endpoint every 2 seconds
- Displays the plan when completed
- Shows error messages if the job fails

## Environment Variables

- `NEXT_PUBLIC_API_HOST` - Backend API host URL (default: `http://localhost:8000`)

## Tech Stack

- Next.js 14
- React 18
- TypeScript
- Tailwind CSS

