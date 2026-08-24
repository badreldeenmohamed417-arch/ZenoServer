## Zeno AI - FastAPI Backend Server
Welcome to the backend architecture of Zeno, an AI-powered educational platform engineered to help students interact with their curriculum using customized Retrieval-Augmented Generation (RAG).

Note for Judges: This entire backend system, database architecture, and RAG pipeline were designed, developed, and documented 100% by a Solo Developer within the tight constraints of the hackathon.

------------------------------
## Tech Stack & Architecture
The server is built with a modern, high-performance asynchronous Python stack designed for speed, scalability, and robust AI integrations:

* Framework: FastAPI (Asynchronous request handling for real-time mobile streaming/chat).
* Database & ORM: PostgreSQL with SQLAlchemy (Async session management) and Alembic for migrations.
* AI Engine & LLM: Google Gemini API via LangChain/Google GenAI SDK.
* Vector Search (RAG): Processing, chunking, and embedding educational PDFs to supply curriculum-aware contexts.
* Authentication: JWT (JSON Web Tokens) with Secure Password Hashing (Passlib & Bcrypt) for email verification, access, and refresh token cycles.

------------------------------
## Key Backend Capabilities Implemented

   1. Curriculum-Aware RAG Pipeline: Processes and indexes complex, bilingual (Arabic/English) educational PDF textbooks into context-rich chunks for highly accurate, non-generic AI tutoring.
   2. Robust Auth & Session Management: Complete enterprise-grade user lifecycle including secure signup, email verification simulation, login, and secure refresh token handling.
   3. Smart Study Sessions API: Dedicated endpoints designed to sync and drive the Android frontend's production features (Pomodoro states, background focus audio metadata, and context-linked AI queries).
   4. Bilingual Text Handling: Optimized database layers and prompt engineering tailored to seamlessly manage right-to-left (RTL) Arabic text alongside left-to-right (LTR) English text without breaking payload layouts.

------------------------------
## System Architecture Overview

[ Android App (Kotlin) ] 
          │
          ▼ (Secure HTTPS / JWT Auth)
┌────────────────────────────────────────────────────────┐
│                   FastAPI Server                       │
│                                                        │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────┐  │
│  │  Auth Router │   │ Study Router │   │ Chat/RAG   │  │
│  └──────┬───────┘   └──────┬───────┘   └─────┬──────┘  │
└──       │                  │                 │      ───┘
          ▼                  ▼                 ▼
   ┌──────────────┐   ┌──────────────┐   ┌────────────┐
   │ PostgreSQL DB│   │ App Logic    │   │ Gemini LLM │
   │ (Users/Sess) │   │ (Pomodoro)   │   │  Vector DB │
   └──────────────┘   └──────────────┘   └────────────┘

------------------------------
## Local Setup & Installation
To run the backend environment locally for testing or evaluation, follow these steps:
## 1. Clone the Repository

git clone https://github.com
cd ZenoServer

## 2. Set Up a Virtual Environment

python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

## 3. Install Dependencies

pip install -r requirements.txt

## 4. Run Database Migrations

alembic upgrade head

## 5. Start the FastAPI Server

uvicorn app.main:app --reload

The interactive Swagger API documentation will be available locally at 127.0.0.
------------------------------
## Reflection & What I Learned (As a Solo Developer)
Building Zeno's server proved that creating an impact-driven EdTech solution involves much more than sending requests to an LLM endpoint. It required engineering a reliable system synchronization layer—handling database transactions, token expiration safeguards, fluid cross-language text processing, and structural safety during network latency.
Zeno succeeds in making AI feel like a deliberate, focused learning companion rather than just another generic chatbot.
------------------------------
Let me know if you want to proceed with:

* The Android frontend README file.
* A LinkedIn post draft to share your achievement.


   └──────────────┘   └──────────────┘   └────────────┘
```

---

## Local Setup & Installation

To run the backend environment locally for testing or evaluation, follow these steps:

### 1. Clone the Repository
```bash
git clone https://github.com<your-username>/zeno-backend.git
cd zeno-backend
```

### 2. Set Up a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory and configure the following parameters:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/zenodb
SECRET_KEY=your_super_secret_jwt_signing_key
GEMINI_API_KEY=your_google_gemini_api_key
ENVIRONMENT=development
```

### 5. Run Database Migrations
```bash
alembic upgrade head
```

### 6. Start the FastAPI Server
```bash
uvicorn app.main:app --reload
```
The interactive Swagger API documentation will be available locally at `http://127.0.0`.

---

## Reflection & What I Learned (As a Solo Developer)
Building Zeno's server proved that creating an impact-driven EdTech solution involves much more than sending requests to an LLM endpoint. It required engineering a reliable system synchronization layer—handling database transactions, token expiration safeguards, fluid cross-language text processing, and structural safety during network latency. 

*Zeno succeeds in making AI feel like a deliberate, focused learning companion rather than just another generic chatbot.*
