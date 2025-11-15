# RezumAI - AI-Powered Resume Management System

An intelligent resume management platform that leverages Google Vertex AI for semantic search, document analysis, and AI-powered chat interactions with resume data.

## 🚀 Quick Start with Docker

Run the entire application with a single command:

```bash
docker-compose up --build
```

This will start:
- **Backend API** (FastAPI) at `http://localhost:8000`
- **Frontend** (React) at `http://localhost:8081`

### Access the Application

Once running, open your browser to:
- **Main Application**: http://localhost:8081
- **Upload Resumes**: http://localhost:8081/upload
- **AI Chat Assistant**: http://localhost:8081/chat
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/healthz

## 🛑 Managing Docker Containers

### Stop the Application
```bash
docker-compose down
```

### View Logs
```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Frontend only
docker-compose logs -f frontend
```

### Rebuild from Scratch
```bash
docker-compose down -v
docker-compose up --build
```

## 🏗️ Architecture

```
┌─────────────────┐
│   Frontend      │
│  (React/Vite)   │
│  Port: 8081     │
└────────┬────────┘
         │
         │ HTTP API
         ↓
┌─────────────────┐
│   Backend       │
│   (FastAPI)     │
│   Port: 8000    │
└────────┬────────┘
         │
         ├─→ Google Cloud Storage (PDF storage)
         ├─→ Firestore (Vector embeddings)
         └─→ Vertex AI (Gemini + Embeddings)
```

## 🛠️ Technology Stack

### Frontend
- React with TypeScript
- Vite for build tooling
- Tailwind CSS & shadcn-ui for styling
- React Router for navigation
- React Query for state management

### Backend
- FastAPI (Python 3.11)
- Google Cloud AI Platform
  - Vertex AI Gemini (gemini-2.0-flash-001)
  - Text Embeddings (text-embedding-004)
- Google Cloud Storage
- Firestore for vector storage
- Uvicorn ASGI server

## 📋 Requirements

- Docker Desktop installed and running
- Docker Compose v3.8+
- At least 4GB RAM allocated to Docker
- Google Cloud Platform account with:
  - Service account JSON key
  - Vertex AI API enabled
  - Cloud Storage bucket created
  - Firestore database created

## ⚙️ Configuration

All environment variables are configured in `docker-compose.yml`. Key configurations:

- `PROJECT_ID`: Your GCP project ID
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account JSON
- `BUCKET_NAME`: GCS bucket for resume storage
- `VERTEX_EMBED_MODEL`: text-embedding-004
- `VERTEX_GEN_MODEL`: gemini-2.0-flash-001

## 🔧 Development

The Docker setup includes hot-reload for both services:
- **Backend**: Auto-reloads on code changes via Uvicorn
- **Frontend**: Auto-reloads on code changes via Vite HMR

## 📊 Features

- **Resume Upload**: Drag-and-drop PDF resume upload
- **Automatic Processing**: Text extraction and chunking
- **Vector Embeddings**: Semantic search using Vertex AI embeddings
- **AI Chat**: Query resumes using natural language
- **Batch Management**: Organize resumes by recruitment batches
- **Cloud Storage**: Secure storage with Google Cloud Storage

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Find and kill processes on ports 8000 or 8081
lsof -ti:8000 | xargs kill -9
lsof -ti:8081 | xargs kill -9
```

### Build Errors
```bash
docker-compose down -v
docker system prune -f
docker-compose up --build
```

### Backend Authentication Issues
- Verify service account JSON path in `docker-compose.yml`
- Ensure service account has required permissions:
  - Vertex AI User
  - Storage Object Admin
  - Cloud Datastore User

### Frontend Can't Reach Backend
- Ensure backend container is healthy: `docker-compose ps`
- Check backend logs: `docker-compose logs backend`
- Verify CORS settings in backend

## 📝 API Endpoints

- `POST /upload_resume`: Upload and process resume
- `POST /api/chat`: Query resumes using AI
- `GET /healthz`: Health check endpoint
- `GET /docs`: Interactive API documentation

## 🤝 Contributing

1. Clone the repository
2. Create a feature branch
3. Make your changes
4. Test with Docker: `docker-compose up --build`
5. Submit a pull request

## 📄 License

[Add your license here]

## 👥 Authors

Team Finetuners(
    Puru Thakur,
    Devank Srivastava,
    Aryan Prasad Singh
)
