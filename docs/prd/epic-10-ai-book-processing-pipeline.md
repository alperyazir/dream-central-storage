# Epic 10: AI Book Processing Pipeline

**Estimated Effort:** 3-4 weeks | **Status:** Done

Implement automated AI processing when books are uploaded to DCS. Extract text from PDFs, segment by pages and modules, use AI to extract topics and vocabulary, generate audio pronunciations, and store all AI-generated data under `/ai-data/` for consumption by Dream LMS.

**What Currently Exists:** Book upload, storage, and basic metadata management
**What We Build:** PDF extraction + AI analysis + Vocabulary extraction + Audio generation + Storage structure

**Consumers:**
- Dream LMS (Epic 13: DreamAI) - uses pre-processed data for content generation

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DCS AI PROCESSING PIPELINE                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Book Upload                                                        │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 1: PDF Text Extraction                                 │   │
│  │  • Extract text from all pages                               │   │
│  │  • Preserve page boundaries                                  │   │
│  │  • Handle scanned PDFs (OCR via Gemini Vision)              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 2: Module Segmentation                                 │   │
│  │  • Detect module/unit/chapter boundaries                    │   │
│  │  • Use book structure hints (TOC, headers)                  │   │
│  │  • AI-assisted segmentation if needed                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 3: AI Analysis                                         │   │
│  │  • Extract topics per module                                 │   │
│  │  • Extract vocabulary with definitions                       │   │
│  │  • Detect language                                           │   │
│  │  • Identify difficulty levels                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 4: Audio Generation                                    │   │
│  │  • Generate pronunciation for each vocabulary word          │   │
│  │  • Multiple languages (word + translation)                  │   │
│  │  • Store as MP3 files                                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 5: Storage                                             │   │
│  │  • Save all data under /ai-data/                            │   │
│  │  • Update book metadata with processing status              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Storage Structure

```
/publishers/{publisher_id}/books/{book_id}/
│
├── content/                        # Original book content (existing)
│   ├── book.pdf
│   ├── pages/
│   └── activities/
│
└── ai-data/                        # NEW: All AI-generated content
    │
    ├── text/                       # Extracted text per page
    │   ├── page_001.txt
    │   ├── page_002.txt
    │   └── ...
    │
    ├── modules/                    # Module data with AI analysis
    │   ├── module_1.json
    │   ├── module_2.json
    │   └── ...
    │
    ├── vocabulary.json             # Master vocabulary list
    │
    ├── audio/                      # Generated audio files
    │   └── vocabulary/
    │       ├── en/                 # English pronunciations
    │       │   ├── word1.mp3
    │       │   └── ...
    │       └── tr/                 # Turkish pronunciations
    │           ├── word1.mp3
    │           └── ...
    │
    └── metadata.json               # Processing metadata
```

---

## Data Schemas

### Module JSON (`modules/module_N.json`)
```json
{
  "module_id": 1,
  "title": "Unit 1: Greetings",
  "pages": [1, 2, 3, 4, 5],
  "text": "Full text content of the module...",
  "topics": ["greetings", "introductions", "basic phrases"],
  "vocabulary_ids": ["hello", "goodbye", "nice_to_meet_you"],
  "language": "en",
  "difficulty": "A1",
  "word_count": 450,
  "extracted_at": "2024-01-15T10:30:00Z"
}
```

### Vocabulary JSON (`vocabulary.json`)
```json
{
  "language": "en",
  "translation_language": "tr",
  "total_words": 150,
  "words": [
    {
      "id": "beautiful",
      "word": "beautiful",
      "translation": "güzel",
      "definition": "pleasing to the senses or mind aesthetically",
      "part_of_speech": "adjective",
      "level": "A2",
      "example": "It's a beautiful day today.",
      "module_id": 3,
      "page": 24,
      "audio": {
        "word": "audio/vocabulary/en/beautiful.mp3",
        "translation": "audio/vocabulary/tr/guzel.mp3"
      }
    }
  ],
  "extracted_at": "2024-01-15T10:30:00Z"
}
```

### Metadata JSON (`metadata.json`)
```json
{
  "book_id": "uuid",
  "processing_status": "completed",
  "processing_started_at": "2024-01-15T10:00:00Z",
  "processing_completed_at": "2024-01-15T10:35:00Z",
  "total_pages": 120,
  "total_modules": 8,
  "total_vocabulary": 150,
  "total_audio_files": 300,
  "languages": ["en", "tr"],
  "primary_language": "en",
  "difficulty_range": ["A1", "A2", "B1"],
  "llm_provider": "deepseek",
  "tts_provider": "edge",
  "errors": []
}
```

---

## Stories

### Infrastructure Stories

#### Story 10.1: LLM Provider Abstraction Layer

**Description:** Create abstracted LLM service for AI processing tasks.

**Acceptance Criteria:**
- [ ] Abstract interface for LLM providers
- [ ] DeepSeek provider implementation
- [ ] Gemini provider implementation (with vision)
- [ ] Environment-based configuration
- [ ] Automatic fallback on failure
- [ ] Usage/cost tracking

**Technical Notes:**
- Shared design with LMS Epic 13
- Can be extracted to shared package later

---

#### Story 10.2: TTS Provider Abstraction Layer

**Description:** Create abstracted TTS service for audio generation.

**Acceptance Criteria:**
- [ ] Abstract interface for TTS providers
- [ ] Edge TTS provider implementation (primary, free)
- [ ] Azure TTS provider implementation (fallback)
- [ ] Multi-language voice selection
- [ ] Batch processing support
- [ ] Audio format configuration (MP3)

---

#### Story 10.3: AI Processing Queue System

**Description:** Implement background job queue for book processing.

**Acceptance Criteria:**
- [ ] Job queue for processing tasks (Redis/Celery or similar)
- [ ] Processing status tracking
- [ ] Progress reporting (percentage)
- [ ] Error handling and retry logic
- [ ] Concurrent processing limits
- [ ] Priority queue for re-processing

**Technical Notes:**
- Processing is async - don't block upload
- Webhook/callback when complete
- Admin can view queue status

---

### Processing Stories

#### Story 10.4: PDF Text Extraction Pipeline

**Description:** Extract text content from uploaded book PDFs.

**Acceptance Criteria:**
- [ ] Extract text from PDF using PyPDF or similar
- [ ] Preserve page boundaries
- [ ] Handle multi-column layouts
- [ ] Detect and handle scanned PDFs (no selectable text)
- [ ] For scanned PDFs, use Gemini Vision for OCR
- [ ] Store extracted text per page
- [ ] Handle extraction errors gracefully

**Technical Notes:**
- Libraries: `pypdf`, `pdfplumber`, or `pymupdf`
- Scanned PDF detection: check if text extraction yields minimal content
- Gemini Vision: send page as image, request text extraction

---

#### Story 10.5: Module Segmentation Logic

**Description:** Segment extracted text into logical modules/units/chapters.

**Acceptance Criteria:**
- [ ] Detect module boundaries from headers/titles
- [ ] Use table of contents if available
- [ ] AI-assisted segmentation for unclear structures
- [ ] Manual module definition override (admin)
- [ ] Handle books with no clear module structure
- [ ] Map pages to modules

**Segmentation Strategies:**
1. **Header-based:** Detect "Unit X", "Chapter X", "Module X" patterns
2. **TOC-based:** Parse table of contents for structure
3. **AI-assisted:** Ask LLM to identify logical segments
4. **Page-range:** Manual definition by admin

---

#### Story 10.6: AI Topic Extraction

**Description:** Use AI to extract topics and themes from each module.

**Acceptance Criteria:**
- [ ] Analyze module text with LLM
- [ ] Extract 3-5 key topics per module
- [ ] Identify grammar points (for language books)
- [ ] Detect difficulty level (A1-C2 for language)
- [ ] Language detection
- [ ] Store topics in module JSON

**Prompt Template:**
```
Analyze this educational content and extract:
1. Main topics (3-5)
2. Grammar points (if language learning)
3. Difficulty level (A1/A2/B1/B2/C1/C2)
4. Target skills (reading, writing, speaking, listening)

Content:
{module_text}
```

---

#### Story 10.7: AI Vocabulary Extraction

**Description:** Extract vocabulary words with definitions and metadata.

**Acceptance Criteria:**
- [ ] Identify vocabulary words in each module
- [ ] Generate definitions for each word
- [ ] Provide translation (if bilingual book)
- [ ] Detect part of speech
- [ ] Extract example sentences from book
- [ ] Assign difficulty level per word
- [ ] Deduplicate across modules
- [ ] Create master vocabulary.json

**Prompt Template:**
```
Extract vocabulary from this educational text:
- Identify key vocabulary words for language learners
- For each word provide: definition, part of speech, example from text
- Focus on words at {difficulty} level
- Provide Turkish translation if applicable

Text:
{module_text}

Return as JSON array.
```

---

#### Story 10.8: Vocabulary Audio Generation

**Description:** Generate audio pronunciations for all vocabulary words.

**Acceptance Criteria:**
- [ ] Generate MP3 for each vocabulary word
- [ ] Support multiple languages (word + translation)
- [ ] Appropriate voice selection per language
- [ ] Store in `/ai-data/audio/vocabulary/{lang}/`
- [ ] Update vocabulary.json with audio paths
- [ ] Batch processing for efficiency
- [ ] Handle TTS failures gracefully

**Audio Generation:**
- English words: `en-US-JennyNeural` or `en-GB-SoniaNeural`
- Turkish words: `tr-TR-EmelNeural` or `tr-TR-AhmetNeural`
- Other languages: Auto-select appropriate voice

---

#### Story 10.9: AI Data Storage Structure

**Description:** Implement storage structure for AI-generated data.

**Acceptance Criteria:**
- [ ] Create `/ai-data/` directory structure on processing start
- [ ] Store text files per page
- [ ] Store module JSON files
- [ ] Store vocabulary.json
- [ ] Store audio files organized by language
- [ ] Store metadata.json with processing info
- [ ] Atomic writes (prevent partial data)
- [ ] Cleanup on re-processing

---

### API Stories

#### Story 10.10: Processing Trigger API

**Description:** API to trigger AI processing for books.

**Acceptance Criteria:**
- [ ] POST endpoint to trigger processing
- [ ] Options: full reprocess, vocabulary only, audio only
- [ ] Return job ID for tracking
- [ ] Validate book exists and has PDF
- [ ] Rate limiting per publisher
- [ ] Admin override for priority processing

**Endpoints:**
```
POST /api/v1/books/{book_id}/process-ai
GET /api/v1/books/{book_id}/process-ai/status
DELETE /api/v1/books/{book_id}/ai-data  # Clear and reprocess
```

---

#### Story 10.11: AI Data Retrieval API

**Description:** API endpoints for LMS to fetch AI-processed data.

**Acceptance Criteria:**
- [ ] GET modules list for a book
- [ ] GET single module with full data
- [ ] GET vocabulary (full list or by module)
- [ ] GET vocabulary audio URL
- [ ] GET processing status and metadata
- [ ] Proper caching headers
- [ ] 404 if not processed yet

**Endpoints:**
```
GET /api/v1/books/{book_id}/ai-data/metadata
GET /api/v1/books/{book_id}/ai-data/modules
GET /api/v1/books/{book_id}/ai-data/modules/{module_id}
GET /api/v1/books/{book_id}/ai-data/vocabulary
GET /api/v1/books/{book_id}/ai-data/vocabulary?module={id}
GET /api/v1/books/{book_id}/ai-data/audio/vocabulary/{lang}/{word}.mp3
```

---

#### Story 10.12: Auto-Processing on Upload

**Description:** Automatically trigger AI processing when new books are uploaded.

**Acceptance Criteria:**
- [ ] Hook into book upload completion event
- [ ] Queue AI processing job automatically
- [ ] Configurable: auto-process on/off per publisher
- [ ] Skip if book already processed (unless forced)
- [ ] Notify admin on processing completion
- [ ] Handle upload of updated book (re-process)

---

### Admin Stories

#### Story 10.13: Admin Processing Dashboard

**Description:** Admin UI to monitor and manage AI processing.

**Acceptance Criteria:**
- [ ] View all books with processing status
- [ ] Filter: processed, pending, failed, not started
- [ ] Trigger manual processing
- [ ] View processing progress
- [ ] View and clear errors
- [ ] Bulk re-process action
- [ ] Processing queue view

**Status Values:**
- `not_started` - No AI processing done
- `queued` - In processing queue
- `processing` - Currently being processed
- `completed` - Successfully processed
- `failed` - Processing failed (with error details)
- `partial` - Some steps completed, others failed

---

#### Story 10.14: Processing Configuration

**Description:** Admin configuration for AI processing settings.

**Acceptance Criteria:**
- [ ] Enable/disable auto-processing globally
- [ ] Configure per-publisher auto-processing
- [ ] Set processing priority rules
- [ ] Configure LLM/TTS provider preferences
- [ ] Set vocabulary extraction depth
- [ ] Configure languages for audio generation
- [ ] Cost limits and alerts

---

## Environment Variables

```bash
# LLM Providers
DEEPSEEK_API_KEY=sk-xxx
GEMINI_API_KEY=xxx

# TTS Providers
AZURE_TTS_KEY=xxx
AZURE_TTS_REGION=turkeycentral

# Processing Configuration
AI_PROCESSING_ENABLED=true
AI_AUTO_PROCESS_ON_UPLOAD=true
AI_PROCESSING_CONCURRENCY=3
AI_MAX_VOCABULARY_PER_BOOK=500
AI_AUDIO_LANGUAGES=en,tr

# Queue Configuration
REDIS_URL=redis://localhost:6379
AI_PROCESSING_QUEUE=ai_processing

# Provider Selection
LLM_PRIMARY_PROVIDER=deepseek
LLM_FALLBACK_PROVIDER=gemini
TTS_PRIMARY_PROVIDER=edge
TTS_FALLBACK_PROVIDER=azure
```

---

## Processing Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     BOOK UPLOAD EVENT                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Auto-process    │
                    │ enabled?        │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │ Yes                         │ No
              ▼                             ▼
    ┌─────────────────┐           ┌─────────────────┐
    │ Queue AI Job    │           │ Wait for manual │
    └────────┬────────┘           │ trigger         │
             │                    └─────────────────┘
             ▼
    ┌─────────────────┐
    │ Worker picks up │
    │ job from queue  │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ 1. Extract PDF  │──────────┐
    │    text         │          │ On Error
    └────────┬────────┘          │
             │                   ▼
             ▼            ┌─────────────┐
    ┌─────────────────┐   │ Mark failed │
    │ 2. Segment into │   │ Log error   │
    │    modules      │   │ Notify admin│
    └────────┬────────┘   └─────────────┘
             │
             ▼
    ┌─────────────────┐
    │ 3. AI extract   │
    │    topics/vocab │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ 4. Generate     │
    │    audio        │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ 5. Store all    │
    │    in ai-data/  │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ 6. Update       │
    │    metadata     │
    │    Mark complete│
    └─────────────────┘
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Processing success rate | > 95% |
| Average processing time (100-page book) | < 5 minutes |
| Vocabulary extraction accuracy | > 90% |
| Audio generation success | > 99% |
| Storage cost per book | < $0.10 |

---

## Phase 2 Features (Not in Scope)

- Full audiobook generation (reading all pages)
- Image extraction and analysis
- Automatic activity generation (done in LMS)
- Multi-book vocabulary aggregation
- Vocabulary difficulty progression tracking

---

## Deliverables

1. LLM provider abstraction (DeepSeek + Gemini)
2. TTS provider abstraction (Edge TTS + Azure)
3. Background job queue for processing
4. PDF text extraction pipeline
5. Module segmentation logic
6. AI topic and vocabulary extraction
7. Audio generation for vocabulary
8. Storage structure under `/ai-data/`
9. API endpoints for LMS consumption
10. Admin processing dashboard
