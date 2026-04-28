# ClauseCheck-NLP

ClauseCheck is a **bilingual (English/Hindi) AI-powered legal contract analyzer**. It is designed to automatically parse, analyze, and grade legal documents by passing them through a comprehensive 14-step Natural Language Processing (NLP) pipeline.

## 🚀 Key Features

- **Bilingual Support**: Analyzes both English and Hindi contracts (lazy loading implemented for Hindi `Stanza` models).
- **Comprehensive NLP Pipeline**: 14-step processing pipeline including parsing, Optical Character Recognition (OCR), clause segmentation, and named entity recognition (NER).
- **Risk & Compliance Detection**: Scans for 10 distinct risk pattern categories and checks for the presence of 12 essential clauses.
- **Privacy-First Architecture**: Documents are processed entirely in-memory and promptly cleared via garbage collection (`gc.collect()`). 
- **Premium UI**: Sleek dark-mode interface built with React/Vite featuring glassmorphism design, SVG score gauges, and a dashboard for historical analysis.
- **Graceful Degradation**: Features like OCR (via Tesseract) are optional, and Supabase integration has an in-memory fallback for immediate local development.

## 🛠️ Tech Stack

### Backend
* **Framework:** FastAPI
* **NLP & ML:** spaCy (`en_core_web_sm`), Stanza, TF-IDF (for extractive summarization)
* **OCR:** PaddleOCR
* **Database:** Supabase Client (with in-memory fallback)

### Frontend
* **Framework:** React + Vite
* **Styling:** Custom CSS (Glassmorphism, Dark-mode first)
* **Data Visualization:** Chart.js

---

## 🏗️ Architecture & Pipeline

ClauseCheck processes uploaded documents via the following **14-step pipeline**:

1. **Validate** file type and size.
2. **Parse** document (Supports PDF, DOCX, TXT).
3. **OCR** scanned elements using PaddleOCR.
4. **Detect** language (Hindi or English).
5. **Segment** text into distinct legal clauses.
6. **Extract** Named Entities (NER using spaCy + Stanza + Regex).
7. **Detect** obligations via modal verb analysis.
8. **Analyze** risks across 10 pattern categories.
9. **Check** compliance for 12 standard legal clauses.
10. **Generate** bilingual explanations (English & Hindi).
11. **Summarize** the core document text.
12. **Store** processing results securely (Supabase).
13. **Return** detailed JSON response.
14. **Delete** raw documents securely from memory.

---

## ⚙️ How to Run Locally

### Prerequisites
- Node.js (v16 or higher)
- Python 3.9+

### 1. Backend Setup

Navigate to the backend directory and install dependencies:

```bash
cd backend
pip install -r requirements.txt
```

Download the English spaCy model:

```bash
python -m spacy download en_core_web_sm
```

*(Optional)* Configure Supabase. Copy `.env.example` to `.env` and enter your credentials. If you skip this, the backend will automatically use its in-memory fallback.

Start the FastAPI server:

```bash
uvicorn main:app --reload --port 8000
```
> The API will be available at `http://localhost:8000`

### 2. Frontend Setup

In a new terminal window, navigate to the frontend directory:

```bash
cd frontend
npm install
npm run dev
```

> Open **http://localhost:5173** in your browser to access the ClauseCheck UI.

---

## 📁 Repository Structure

```text
ClauseCheck-NLP/
├── backend/
│   ├── main.py                    # FastAPI entrypoint
│   ├── routers/                   # API routes (analyze, history)
│   ├── services/                  # NLP Modules (OCR, NER, Segmentation, Summarizer)
│   └── db/                        # Supabase & Memory fallback logic
├── frontend/
│   ├── src/
│   │   ├── components/            # Reusable UI components (ScoreGauge, RiskBadge)
│   │   ├── pages/                 # Upload, Results, and History pages
│   │   └── index.css              # Design system
│   └── index.html
└── ...                            # SRS, update logs, and implementation plans
```

## 📜 License

[MIT License](LICENSE) (or state your specific license here).
