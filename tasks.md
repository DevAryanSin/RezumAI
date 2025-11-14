Hi Lovable — build the Next.js (App Router) frontend for RezumAI, an AI-powered resume search + conversational assistant for recruiters. Use the PPT/idea details as the source of truth for feature scope and UI specifics. (Source: uploaded idea PPT). 

Finetuners_HackFest2025_Idea Su…

Below is a ready-to-run, developer-focused prompt that includes pages, components, API contracts, UX flows, integrations (Agora, file upload, chat), Tailwind styling guidelines, accessibility, and acceptance criteria. Deliver a production-ready Next.js frontend (TypeScript + Tailwind) that can plug into the backend described in the PPT.

Project summary (one-liner)

Build a responsive Next.js (App Router) frontend that lets recruiters upload resumes (PDF/DOCX), view parsed candidate cards, run natural-language searches, and have a RAG-powered conversational assistant (chat + optional voice) via Agora. Include shortlisting, comments/tags, and PII redaction UI.

(Reference: Tech stack and frontend responsibilities per PPT). 

Finetuners_HackFest2025_Idea Su…

High-level requirements

Framework: Next.js (App Router), TypeScript.

UI: Tailwind CSS (mobile-first, responsive, accessible).

Chat: Agora RTM/voice integration for real-time chat & optional voice.

File upload: resumable upload to backend (Cloud Storage). Show progress, validation, and parsed-status.

State: client-side caching + optimistic UI for shortlists/tags. Integrate with REST/WS backend API endpoints (contracts below).

Components must be reusable, testable, and documented (Storybook-friendly).

Accessibility: keyboard navigation, ARIA labels, color contrast.

Security: avoid exposing tokens in client code; use secure token fetch endpoints.

Pages & Routes

Use Next.js App Router (/app) and nested layouts.

/ (Dashboard)

Recruiter summary, KPI cards, quick search box, recent uploads, and top shortlists.

/upload

Multi-file drag-and-drop upload area (PDF/DOCX).

Upload queue, per-file progress bar, parsed status, and preview link.

/candidates (list + filters)

Search bar (natural language).

Filters: experience range, skills, location, education, availability.

Candidate cards grid/list with score, snippets, tags, and actions.

/candidate/[id] (profile)

Full parsed JSON view (work items, education, skills, projects).

Evidence snippets with highlighted matching text.

Actions: Shortlist, Add comment, Tag, Redact PII.

/chat (conversational agent)

Left panel: query history and saved prompts.

Main panel: chat interface with RAG responses, candidate references, and recommended actions.

Right panel: context drawer showing retrieved snippets and candidate cards used in last response.

/settings

Agora token endpoint config, privacy & PII settings, retention policy toggles.

Key Components (props + responsibilities)

Design components as TypeScript React components.

UploadDropzone
Props: onUpload(files), acceptedTypes, maxSizeMB
Responsibilities: drag-drop, multi-select, validate, show preview and progress.

UploadQueueItem
Props: file, status, progress, onCancel, onRetry
Show parsed status (parsing / parsed / error) and link to candidate record when parsed.

SearchBar
Props: onSearch(query), placeholder, debounceMs
Supports natural language queries and triggers embedding search.

CandidateCard
Props: candidate, matchScore, snippets, onShortlist, onOpen
UI: photo/avatar, score badge (0–100), 3-line summary, evidence snippets, tags, actions.

CandidateProfile
Props: candidateId
Responsibilities: fetch parsed JSON, show timeline of work experiences, skills cloud, projects, download original resume, redact PII button.

ChatWindow
Props: sessionId, userId
Responsibilities: conversation UI, streaming LLM responses, show citations (snippets + candidate links), quick actions in responses (shortlist this candidate).

AgoraVoiceButton
Props: onStart, onStop, isRecording
Uses Agora SDK to start voice, then stream transcript to backend.

TagInput, CommentsPanel, ShortlistButton, PIIRedactModal

UI/UX & Design Notes

Use Tailwind with a clean modern look (cards, soft shadows, rounded corners).

Candidate cards should have clear visual hierarchy: name, title, match score (prominent), top 3 skills, 1-2 snippet lines with highlighted keywords.

Chat must show the RAG-sourced snippets with “evidence” badges linking to candidate card/profile.

Provide micro-copy for empty states (e.g., "No matching candidates — try broadening the query").

Mobile-first: stack panels vertically on small screens; show right-hand context drawer only on large screens.

Integration & API Contracts (backend endpoints the frontend will call)

Design frontend to be backend-agnostic but expect these REST/WS endpoints:

Auth / tokens

GET /api/auth/session → returns { userId, name, email, roles }

GET /api/agoaratoken?uid=<uid> → returns { token } (for Agora). Token fetch must be server-side (no secrets on client).

File upload & parse

POST /api/upload/init → returns { uploadId, uploadUrl } (signed URL)

Client PUT to uploadUrl (or use resumable upload).

GET /api/upload/status?uploadId= → returns { status: 'uploaded'|'parsing'|'parsed'|'error', candidateId? }

GET /api/candidate/:id/raw → returns parsed JSON and links to original file.

Embedding search / candidates

POST /api/search body: { query: string, filters?: {...}, topK?: number }
returns:

{
  "results": [
    {
      "candidateId": "c_123",
      "score": 87,
      "snippets": [
        { "text": "Built microservices using Kubernetes", "location": "...", "evidenceId": "e_1" }
      ],
      "highlights": ["Kubernetes", "microservices"],
      "metadata": { "experienceYears": 6, "currentCompany": "X" }
    }
  ],
  "queryId": "q_456"
}

Chat (RAG)

WebSocket /api/chat/ws?sessionId= OR REST streaming endpoint:

Send: { sessionId, userId, message, context?: { candidateIds: [] } }

Receive streaming tokens and final message with references: [{ candidateId, snippet }].

Shortlist / actions / comments

POST /api/candidate/:id/shortlist body: { recruiterId, reason }

POST /api/candidate/:id/comments body: { recruiterId, comment }

POST /api/candidate/:id/tags body: { tags: ["backend","kubernetes"] }

POST /api/candidate/:id/redact body: { fields: ["email","phone"] } returns redacted view

Agora voice transcript capture

POST /api/transcripts body: { sessionId, transcriptChunk, timestamp } (backend will attach to chat)

Expected data flows

Recruiter uploads resume → frontend posts to /api/upload/init → upload to signed URL → poll /api/upload/status → when parsed, show candidate card and index in /candidates.

Recruiter types natural-language query → frontend calls /api/search → shows candidate cards with scores and snippets.

Recruiter opens /chat and asks “Find senior backend engineers...”: frontend sends chat messages (WS or REST) → receives RAG responses with citations and actions. Quick action buttons let recruiter shortlist / comment without leaving chat.

Recruiter can click “Redact PII” on a candidate profile — frontend calls /api/candidate/:id/redact and updates UI.

UI Behaviors & Micro-interactions

Candidate match score: animate from 0 → score on load.

Evidence snippet: hover reveals source file and a “jump to position” link.

Shortlist action: optimistic UI (card shows shortlisted badge immediately; rollback on error).

Chat responses: stream tokens, show partial responses, highlight any candidate references as clickable badges.

Error states & loading

Upload failures: show reasons (file too large / unsupported format / network) and retry.

Parsing taking long: show estimated time and allow “notify me” / continue.

Chat disconnected: show reconnect button and degrade gracefully to non-RT streaming.

Testing & quality

Provide unit tests for critical components (UploadDropzone, CandidateCard, ChatWindow).

E2E tests: simulate upload → parse → search → chat.

Accessibility checks: keyboard nav for candidate cards and chat input, aria-live for chat streaming.

Deliverables

Next.js repo scaffold (TypeScript) with App Router and pages above.

Reusable component library (TSX + Tailwind).

Example mock server (/app/api/mock/*) returning sample payloads so UI can be demoed without backend.

Integration stubs for Agora (token fetch + simple client init).

Readme with setup, env vars required (e.g., NEXT_PUBLIC_API_BASE, AGORA_APP_ID), and API contract summary.

Storybook or interactive component showcase (preferred).

Test suite (unit + basic E2E).

Deployment instructions (Vercel/Netlify) with environment variable notes.

Acceptance criteria (how we know it's done)

Recruiter can upload at least one PDF and see a parsed candidate card appear (mocked parser acceptable for demo).

Natural-language search returns candidate cards with scores and snippets (using mock /api/search).

Chat UI can send a message and display streaming responses with candidate citations.

Candidate card supports Shortlist + Add Tag + Comment (persisted to mock API).

Agora token fetch is implemented and Agora client initializes (actual RTC optional for demo but token flow must be present).

Mobile & desktop responsive, accessible, with no major console errors.

Mock data (paste into /app/api/mock/data.ts)
{
  "candidates": [
    {
      "candidateId": "c_123",
      "name": "Asha Kumar",
      "title": "Senior Backend Engineer",
      "experienceYears": 6,
      "currentCompany": "CloudApps",
      "skills": ["Python","Kubernetes","Microservices","GCP"],
      "score": 92,
      "snippets": [
        {"text":"Designed microservices deployed on Kubernetes with 99.9% uptime","source":"Resume.pdf#page=2"}
      ]
    }
  ]
}

Developer notes & priorities from PPT

Focus on Next.js, Tailwind CSS, and Agora for the real-time chat/voice layer.

Make the frontend plug-and-play with the backend architecture described (Document AI → Vertex embeddings → Matching Engine) — expose clear API contracts so backend teams can connect.

Include a Settings page where admin can configure PII redaction toggles and retention policy per the PPT. 

Finetuners_HackFest2025_Idea Su…

Final instructions to Lovable (copy-paste ready)

Build the Next.js (TypeScript) frontend for RezumAI following the detailed spec above. Use Tailwind CSS and keep components modular and accessible. Provide a mock API for demoing all key user flows (upload → parse → search → chat → shortlist). Integrate Agora token flow and UI stubs for voice. Include unit tests and a README with setup & env variables. Prioritize the Dashboard, Upload, Candidates list, Candidate profile, and Chat pages. Use the PPT as the authoritative product source.