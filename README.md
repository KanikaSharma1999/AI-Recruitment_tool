# HireIQ — AI-Powered Recruiter OS

HireIQ is a production-ready, cloud-native Applicant Tracking System (ATS) and recruitment platform. It streamlines candidate workflows — from initial Job Description (JD) parsing to automated resume ranking, chatbot-assisted sourcing, video interviews with AI proctoring, and post-interview analysis reports.

---

## 🚀 Key Features

*   **Job Description (JD) Intelligence:** Automated parsing of JDs using **Groq Cloud API (LLaMA-3.3-70B)** to extract mandatory skills, certifications, domain filters, and target experience criteria.
*   **Deep Resume Parsing:** Extracted PDF/DOCX text parsed via a hybrid engine combining rule-based heuristics, **spaCy Named Entity Recognition (NER)**, and **Groq LLaMA-3.3** timeline extraction.
*   **Vector Search & Semantic Match:** Local text embeddings generated using **SentenceTransformers (`all-MiniLM-L6-v2`)** and indexed with **FAISS** for instant vector similarity search (zero cloud costs).
*   **Weighted Scoring Engine:** A transparent, deterministic mathematical scoring formula combining:
    *   Skills Match (40%)
    *   Experience Alignment (25%)
    *   Semantic Similarity (15%)
    *   Project relevance (10%)
    *   Certifications (5%)
    *   Resume completeness (5%)
*   **Recruiter Copilot Chatbot:** An interactive RAG chatbot allowing natural-language database search, candidate comparisons, and automated hiring query responses.
*   **Live Video Room with Jitsi Meet:** Embeds peer-to-peer audio-video channels directly inside candidate and recruiter screens (no accounts required).
*   **In-Browser AI Proctoring:** Client-side **MediaPipe FaceMesh** eye/gaze tracking, face presence detection, tab-switching triggers, and copy-paste monitors.
*   **Post-Interview Analysis:** Speech-to-text audio transcription via **Groq Whisper** combined with LLaMA narrative synthesis to deliver behavioral assessments, integrity checks, and summary reports.

---

## 🛠 Tech Stack

| Tier | Technology | Purpose |
|------|------------|---------|
| **Frontend** | React, Vite, Recharts, Lucide | Single-Page Application (SPA) dashboard |
| **Backend** | FastAPI, Uvicorn, Pydantic | High-performance, asynchronous REST API |
| **Database** | MongoDB Atlas, Motor | Document database for candidate metadata & status |
| **Vector Index**| FAISS | Local, disk-persisted vector similarity engine |
| **AI Layer** | Groq (LLaMA-3.3-70B), Groq Whisper | Language synthesis, parsing, speech-to-text |
| **Local AI** | SentenceTransformers | Local token vector embedding generation |
| **Proctoring** | MediaPipe FaceMesh | Browser-side gaze and face presence analysis |
| **Automation** | APScheduler | Email reminders and notification dispatcher |

---

## 📂 Project Structure

```
Job_resume_ranker-main/
├── backend/
│   ├── main.py                  # FastAPI server entry point & startup
│   ├── database.py              # MongoDB Motor connections & models
│   ├── auth.py                  # JWT authentication middleware
│   ├── matching.py              # Weighted scoring engine & heuristics
│   ├── resume_parser.py         # NLP text extraction & rule-based parser
│   ├── reports.py               # PDF and Excel report generators
│   ├── routes/                  # API routes (candidates, jobs, auth, chat, etc.)
│   └── services/                # Backend services (LLM, FAISS, SMTP, Whisper)
├── frontend/
│   ├── src/
│   │   ├── pages/               # Views (Dashboard, InterviewRoom, Candidates, etc.)
│   │   ├── components/          # Reusable dashboard panels and cards
│   │   └── context/             # React authentication contexts
│   └── vite.config.js           # Vite development and proxy configuration
├── start_platform.bat          # One-click platform startup batch script
├── PROJECT_WORKFLOW.md          # Technical pipeline manual
└── requirements.txt             # Clean backend python dependencies
```

---

## ⚙️ Setup & Execution

### Prerequisites
*   Python 3.10+
*   Node.js 18+
*   MongoDB Atlas cluster connection string
*   Groq API Key (get yours free at [console.groq.com](https://console.groq.com))

### 1. Configuration
Create a `.env` file inside the `backend/` directory using your credentials:
```env
MONGO_URI=mongodb+srv://<user>:<password>@cluster0.mongodb.net/ats_platform
JWT_SECRET=your_jwt_signing_secret
ENCRYPTION_KEY=g7EuM8O_-qJTOyVDZZTutI-JHTmgWfezf8kHNnH5eOQ=
GROQ_API_KEY=gsk_your_groq_api_key
FRONTEND_URL=http://localhost:5173
SMTP_USERNAME=your_gmail_address
SMTP_PASSWORD=your_gmail_app_password
EMAIL_FROM=your_gmail_address
```

Create a `.env` file in the `frontend/` directory:
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_FRONTEND_URL=http://localhost:5173
```

### 2. Run the platform
Double-click `start_platform.bat` or run:
```bash
# Start FastAPI backend
cd backend
pip install -r requirements.txt
python main.py

# Start React frontend
cd ../frontend
npm install
npm run dev
```

Open `http://localhost:5173` to access the Recruiter Dashboard.
For candidates to join interviews from other machines, set `FRONTEND_URL` to your network IP (e.g. `http://192.168.1.5:5173`) or an active ngrok tunnel.
