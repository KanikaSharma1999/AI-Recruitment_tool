# HireIQ Platform: Technical Architecture & Step-by-Step Workflow Breakdown
This document provides a comprehensive, step-by-step walkthrough of the HireIQ platform's core pipeline, detailing the frontend actions, backend routes, database storage, file handling, and AI services involved in each stage. Use this to explain the system's end-to-end flow to your lead or team.

---

## Phase 1: Job Description (JD) Processing Flow

```
Recruiter UI (Create JD) —[POST /jobs]→ FastAPI Router (routes/jobs.py)
                                     │
                                     ├── 1. Save Raw JD to MongoDB (jobs col)
                                     ├── 2. Call services/llm_parser.py
                                     │    │
                                     │    ▼ (via services/llm_service.py)
                                     │    Groq Cloud API (llama-3.3-70b-versatile)
                                     │    │
                                     │    ▼ (JSON Extracted)
                                     └── 3. Save Structured Requirements to MongoDB
                                          │
                                          ▼ (via services/vector_store.py)
                                     4. Generate Embeddings & Sync FAISS Index
```

### Step-by-Step Execution:

1. **Frontend Action**: The Recruiter enters a job title and pastes the job description (JD) text in the dashboard (`frontend/src/pages/Jobs.jsx`) and clicks "Create Job".
2. **API Call**: A POST request is sent to `/jobs` with the job details.
3. **Database Insertion (Raw)**: The backend router (`backend/routes/jobs.py`) receives the request, generates a unique ID, sets `vector_indexed = False`, and creates an entry in the MongoDB `jobs` collection.
4. **AI Service Call**: The backend invokes `parse_jd_with_llm` in `backend/routes/jobs.py` which interfaces with `backend/services/llm_service.py` to prompt Groq Cloud (`llama-3.3-70b-versatile`) to extract structured requirements (required skills, preferred skills, min experience, certifications, and target project domains).
5. **Local Embedding & Vector Sync**: The backend uses the local `SentenceTransformer("all-MiniLM-L6-v2")` to generate a 384-dimensional vector embedding of the job description. This vector is appended to the jobs FAISS index store (`backend/services/vector_store.py`).
6. **Database Update (Structured)**: The structured payload and embedding indexing flag are saved to the MongoDB `jobs` collection.

---

## Phase 2: Resume Ingest, Cascade Parsing, and Storage Flow

```
Recruiter UI (Upload Resume) —[POST /resumes/upload]→ FastAPI (main.py)
                                                      │
                                                      ├── 1. Read File (PyPDF2 / Mammoth)
                                                      ├── 2. spaCy PERSON NER + Name Guard
                                                      ├── 3. Date Range Regex Scrapers
                                                      ├── 4. Upload to Supabase Storage
                                                      ├── 5. FAISS Reindexing & Embedding
                                                      └── 6. Save Profile to MongoDB (candidates col)
```

### Step-by-Step Execution:

1. **Frontend Action**: The Recruiter drags and drops multiple PDF or DOCX resume files into the system upload queue (`frontend/src/pages/Upload.jsx`).
2. **API Call**: A POST request is sent to `/resumes/upload` containing the multipart file binary streams.
3. **File Extraction**: The backend parser (`backend/resume_parser.py`) processes the files, using `PyPDF2.PdfReader` for PDFs or `mammoth.extract_html` for DOCX files.
4. **Name Guard Filter**: spaCy NER (`en_core_web_sm`) identifies candidate names. The custom regex block title list filters out email addresses, social link strings, and blocklisted words (job titles like "Engineer", "Developer").
5. **Timeline Parsing**: Scans for dates and calculates experience duration through a 3-stage parser (header scanning, date range regexes, and LLM fallback).
6. **Cloud Storage & Cleanup**: The file is uploaded to Supabase Storage. Temporary local copies are immediately deleted, and the public URL is saved.
7. **Local Embedding & Index Sync**: Generates an embedding vector using the local `SentenceTransformer` and inserts it into the FAISS store index.
8. **Database Storage**: Creates a candidate profile in the MongoDB `candidates` collection with stage status set to `applied`.

---

## Phase 3: AI Matching, Weighted Scoring & Decisioning Engine Flow

```
Recruiter UI (Rank Candidates) —[POST /candidates/rerank-all-candidates]→ FastAPI (routes/candidates.py)
                                                                       │
                                                                       ├── 1. Pull JD & Candidates from DB
                                                                       ├── 2. Normalize Skills Synonyms
                                                                       ├── 3. Execute Custom Match Score Formula
                                                                       ├── 4. Call Groq Cloud API (Strengths/Risks)
                                                                       └── 5. Save Scorecards to MongoDB
```

### Step-by-Step Execution:

1. **Frontend Action**: Recruiter clicks "Analyze and Score Candidates" on the dashboard (`frontend/src/pages/Dashboard.jsx`).
2. **API Call**: A POST request is sent to `/candidates/rerank-all-candidates` with the `job_id`.
3. **Database Retrieval**: The SafeCollection proxy pulls the job criteria and candidate profiles.
4. **Skill Synonym Alignment**: Replaces skill variants with canonical representations using the `SKILL_SYNONYMS` vocabulary map in `backend/matching.py`.
5. **Custom Matching Core**: Programmatically calculates the weighted scorecard using the formula:
   $$\text{Score} = \text{Clamped}\Big(0.40(S) + 0.25(E) + 0.15(Sim) + 0.10(P) + 0.05(C) + 0.05(Q) - \sum \text{Penalties}\Big)$$
   Calculates skills exact matches, semantic matches ($\ge 0.72$), partial/fuzzy matches ($\ge 0.50$ or RapidFuzz Levenshtein $\ge 80$), and deducts active negative penalties (experience gap, short resume, low extraction confidence).
6. **AI Service Call**: Calls Groq Llama 3.3 to analyze candidate profiles and output natural language strengths, weaknesses, risks, and onboarding estimate.
7. **Database Update**: Saves overall score, sub-scores, matched/missing skills, risk flags, and LLM summary to the MongoDB `candidates` collection.

---

## Phase 4: Automated Notification & Email Scheduling Flow

```
Recruiter UI (Schedule Call) —[POST /interviews/schedule]→ FastAPI (routes/interviews.py)
                                                         │
                                                         ├── 1. Generate Jitsi Room & UUID Secure Token
                                                         ├── 2. Save Session to MongoDB (interviews col)
                                                         ├── 3. Decrypt SMTP Settings via Fernet Crypt
                                                         └── 4. SSL/TLS SMTP Email Dispatch
```

### Step-by-Step Execution:

1. **Frontend Action**: Recruiter schedules a call time from `frontend/src/components/InterviewModal.jsx`.
2. **API Call**: POST request to `/interviews/schedule` with candidate ID and target date/time.
3. **Session Setup**: Generates a random UUID secure token and hashes the Jitsi room name.
4. **Database Insertion**: Saves the scheduled session to `interview_sessions_col` with status set to `scheduled` and updates the candidate's stage status to `interview_scheduled`.
5. **SMTP Decryption**: Decrypts the SMTP credentials using Cryptography Fernet.
6. **Email Dispatch**: Renders HTML template (`get_interview_scheduled_template`) and runs `smtplib` over SSL/TLS (port 465/587) to send the invite containing the unique secure room join link.

---

## Phase 5: Real-Time Interview & Video Proctoring Flow

```
Candidate UI (Jitsi Video Room) —[WS / REST Event Logs]→ FastAPI (routes/interviews.py)
                                                        │
                                                        ├── 1. Validate UUID Secure Token & Join Window
                                                        ├── 2. Client-Side MediaPipe Mesh Gaze Tracking
                                                        ├── 3. Log Tab Change / Copy-Paste Violations
                                                        └── 4. Calculate integrity Score & Update DB
```

### Step-by-Step Execution:

1. **Frontend Action**: Candidate opens the unique secure interview join link (`frontend/src/pages/CandidateInterview.jsx`).
2. **API Verification**: Endpoint `/interviews/token/{secure_token}` validates the secure token and room availability.
3. **Video Bridge Initialization**: If verification succeeds, Jitsi Meet iframe is mounted.
4. **Client-Side Eye Tracking**: MediaPipe running locally in candidate's browser sandbox calculates facial meshes, iris coordinates, and logs eye deviations or participants counts.
5. **Browser Event Auditing**: Frontend monitors tab switches and copy-paste events.
6. **Database Violation Logging**: Frontend posts proctoring events dynamically to `/interviews/proctoring/event`, updating the database with violation logs.
7. **Integrity Calculation**: Backend calculates and updates the live integrity score: `100 - (tab_switches * 5) - (gaze_deviations * 2) - (multi_face * 5)`.

---

## Phase 6: Audio Chunk Recording, Speech Transcription, and Diarization Flow

```
Candidate Mic —[POST /audio/upload]→ FastAPI (routes/audio.py)
                                    │
                                    ├── 1. Check Offset time from Live Session
                                    ├── 2. Upload raw .webm chunk to Storage
                                    ├── 3. Groq Whisper API (ASR transcribing)
                                    ├── 4. Rule-Based Speaker Diarization
                                    └── 5. Append Dialog to MongoDB collections
```

### Step-by-Step Execution:

1. **Frontend Action**: Frontend records candidate's microphone audio and sends 10-second webm chunk slices.
2. **API Call**: POST request to `/audio/upload` containing the `candidate_id` and raw `.webm` audio chunk.
3. **Session Offset Sync**: Backend calculates elapsed seconds from the start of the live session to determine timestamps.
4. **Cloud Storage**: Audio chunk is uploaded to Supabase Storage, and the temp file is cleaned up.
5. **AI Service Call**: Sends the raw audio bytes to Groq Whisper (`whisper-large-v3`) to receive JSON segments.
6. **Local Diarization**: Runs the `_diarize_segment` rule-based check on each segment. If a segment ends with a question mark or contains interviewer keywords, it is tagged as `"Interviewer"`; otherwise, it is tagged as `"Candidate"`.
7. **Database Persistence**: Appends the speaker-tagged transcript segments to MongoDB `candidates` and `interview_sessions` collections.

---

## Phase 7: AI Post-Interview Evaluation & Report Exporting Flow

```
Recruiter UI (End Call) —[POST /interviews/end]→ FastAPI (routes/interviews.py)
                                                │
                                                ├── 1. Calculate Session Call Duration
                                                ├── 2. Call Groq Cloud API (Evaluate Knowledge)
                                                ├── 3. Update Session & Candidate status
                                                └── 4. Generate ReportLab PDF Exporter
```

### Step-by-Step Execution:

1. **Frontend Action**: Recruiter clicks "End Interview" inside the dashboard call component.
2. **API Call**: POST request to `/interviews/end` with Candidate ID.
3. **AI Post-Call Evaluation**: Fetches transcripts, integrity logs, and speaking times. Calls Groq Llama 3.3 to analyze knowledge level, communication skills, confidence, and filler word count.
4. **Database Verification**: Updates the session status to `COMPLETED` and the candidate status to `interview_completed`.
5. **PDF scorecard Generation**: Calls the ReportLab service (`backend/reports.py`) to generate a styled PDF report.
6. **File Streaming**: Returns the binary PDF stream directly to the recruiter's browser.

---

## Phase 8: Conversational RAG Chatbot Copilot Flow

```
Recruiter UI (Chat Query) —[POST /chat/stream]→ FastAPI (routes/chat.py)
                                               │
                                               ├── 1. Classify Intent (Regex / Semantic Check)
                                               ├── 2. Construct Mongo / FAISS Query
                                               ├── 3. Build Memory Buffer Context
                                               └── 4. Stream Markdown tokens via SSE
```

### Step-by-Step Execution:

1. **Frontend Action**: Recruiter types a natural language search query in the copilot panel (`frontend/src/components/ChatbotPanel.jsx`).
2. **API Call**: POST request to `/chat/stream` containing query and session ID.
3. **Intent Classification**: Evaluates intent using regex patterns. If a pattern misses, it falls back to a semantic classifier check against target intents (threshold $\ge 0.55$).
4. **Database Query Extraction**: If the intent is candidate search, it queries MongoDB for matching skills, location, or experience.
5. **Context Framing**: Builds a markdown context block containing candidate profiles and conversational memory.
6. **AI Service Call**: Sends the query and database context to Groq Llama 3.3.
7. **SSE Token Streaming**: Streams markdown text tokens back to the recruiter using Server-Sent Events (SSE).
