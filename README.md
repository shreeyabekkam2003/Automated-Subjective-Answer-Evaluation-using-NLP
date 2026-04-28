# Automated Subjective Answer Evaluation System

A web application that automatically grades student answers to subjective questions using NLP — combining semantic similarity, conceptual similarity, and keyword matching to produce a weighted score and final grade.

---

## Overview

Students can either **upload a photo of their handwritten answer sheet** (text extracted via Azure OCR) or **type their answers directly** into the web interface. The system evaluates each answer against three reference key answers and generates a per-question score and an overall grade.

The app is built with a **Flask** backend and plain HTML/CSS/JS frontend.

---

## Features

- Login-protected access
- Upload handwritten answer sheets — Azure Computer Vision OCR extracts text automatically
- Manual answer entry as an alternative to image upload
- Per-question scoring out of 5 marks (10 questions, 50 marks total)
- Detailed results breakdown with final letter grade
- Pre-filled answer fields when text is extracted from uploaded image

---

## Scoring Method

Each student answer is evaluated against **3 reference key answers** using four metrics combined with fixed weights:

| Metric | Weight | Method |
|---|---|---|
| Semantic Similarity | 0.30 | Sentence-BERT (`paraphrase-MiniLM-L6-v2`) cosine similarity |
| Keyword Matching | 0.30 | SpaCy POS-tag based keyword extraction; intersection of keywords across all 3 key answers |
| Conceptual Similarity | 0.20 | SpaCy Word2Vec (`en_core_web_sm`) average token vector cosine similarity |
| Length Similarity | 0.20 | Normalized length comparison against average key answer length |

A hard zero is applied if semantic similarity < 0.2 or keyword match < 0.1 (off-topic answer detection).

**Grading scale (out of 50):**

| Score | Grade |
|---|---|
| ≥ 45 | O — Outstanding |
| ≥ 40 | A — Very Good |
| ≥ 30 | B — Good |
| ≥ 17 | C — Pass |
| < 17 | F — Fail |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| NLP | Sentence-Transformers, SpaCy, NLTK |
| OCR | Azure Cognitive Services — Computer Vision (Read API) |
| Frontend | HTML, CSS, JavaScript |
| Data | Excel (`Key_answers.xlsx`) for reference answers |

---

## Project Structure

```
├── app.py                         # Flask app — routes, scoring logic, OCR integration
├── Automated_Subjective_Answer_Evaluation.ipynb  # NLP scoring pipeline (development/research)
├── Key_answers.xlsx               # Reference key answers (3 per question, 10 questions)
├── templates/
│   ├── index.html                 # Login page
│   ├── upload.html                # Upload image or go to manual entry
│   ├── ques.html                  # Answer entry form (10 DBMS questions)
│   ├── evaluate.html              # Answer status review before submission
│   └── results.html               # Score and grade display
└── static/
    ├── script.js                  # Image preview on upload page
    └── page.css                   # Shared styles
```

---

## Application Flow

```
Login → Upload Answer Sheet (OCR) ──┐
          OR                        ├──→ Review Answers → Evaluate → Results
        Enter Answers Manually ─────┘
```

1. **Login** — `admin / password`
2. **Upload** — submit a photo of a handwritten answer sheet; Azure OCR extracts answers per question number
3. **Questions page** — review or edit extracted answers, or type answers from scratch
4. **Evaluate** — shows which questions are answered / unanswered before final submission
5. **Results** — displays total score, final grade, and per-question breakdown

---

## Setup

```bash
pip install flask sentence-transformers spacy nltk scikit-learn pandas openpyxl \
            azure-cognitiveservices-vision-computervision msrest

python -m spacy download en_core_web_sm
```

Set Azure credentials as environment variables:
```bash
export VISION_KEY="your_azure_key"
export VISION_ENDPOINT="your_azure_endpoint"
```

```bash
python app.py
```

---

## Notebook

`Automated_Subjective_Answer_Evaluation.ipynb` contains the standalone NLP pipeline used to prototype and test the scoring functions — including the Sentence-BERT setup, SpaCy similarity calculations, keyword extraction logic, and an optional SBERT fine-tuning loop using contrastive loss.
