# Resume Processing & ATS System

A comprehensive resume analysis system that processes PDF resumes, calculates ATS scores, and finds matching job opportunities.

## Main Features

- **PDF Resume Processing**: Extract text, skills, and metadata from resume PDFs
- **ATS Scoring**: Comprehensive ATS analysis with detailed scoring breakdown
- **Job Matching**: Intelligent job matching based on skills, experience, and semantic similarity
- **NLP Analysis**: Extract skills, keywords, and entities using spaCy
- **Embedding Generation**: Convert text to vectors for semantic matching
- **Database Storage**: SQLite database with full-text and vector search
- **Background Processing**: Celery workers for async processing
- **Job Feeding**: CSV-based job posting ingestion

## Core Workflow

```
Frontend → Upload Resume PDF → Server Processing:
    ├─ Text Extraction (PyPDF2)
    ├─ NLP Analysis (spaCy)
    ├─ Embedding Generation (SentenceTransformers)
    ├─ ATS Scoring (Multi-criteria analysis)
    ├─ Job Matching (Similarity + Skills + Experience)
    └─ Database Storage
    ↓
Return: ATS Score + Matching Jobs + Recommendations
```

## ATS Scoring Algorithm

The ATS system evaluates resumes across 5 key criteria:

### 1. Format & Structure Score (25%)
- **Section Detection**: Summary, Experience, Education, Skills sections
- **Text Length**: Optimal 500-2000 words
- **Contact Information**: Phone, email, social profiles
- **Formatting**: Bullet points, professional structure
- **Professional Language**: Action verbs and professional terms

### 2. Skills Score (30%)
- **Technical Skills**: Programming languages, frameworks, tools
- **High-Demand Skills**: Python, AWS, Docker, React, etc.
- **Skill Diversity**: Multiple technology categories
- **Soft Skills**: Communication, leadership, teamwork
- **Skill Relevance**: Industry-specific technical skills

### 3. Experience Score (25%)
- **Years of Experience**: Extracted from resume text
- **Experience Level**: Entry to Senior level mapping
- **Quantification**: Metrics and achievements
- **Career Progression**: Growth indicators

### 4. Education Score (10%)
- **Degree Level**: PhD, Master's, Bachelor's, Associate
- **Relevance**: Field of study alignment
- **Certifications**: Professional certifications

### 5. Keyword Score (10%)
- **Keyword Density**: Optimal 2-5% density
- **Industry Terms**: Sector-specific vocabulary
- **SEO Optimization**: ATS-friendly terminology

## Job Matching Algorithm

### Semantic Similarity (40%)
- Uses cosine similarity between resume and job embeddings
- Captures contextual meaning beyond keywords
- SentenceTransformers model for vector generation

### Skills Compatibility (40%)
- Direct skill matching between resume and job requirements
- Technical skill prioritization
- Skill category analysis

### Experience Level Match (20%)
- Resume experience vs job requirements
- Over-qualification tolerance
- Level appropriateness scoring

## Quick Start

### Automatic Database Initialization
The server automatically initializes SQLite databases and creates all necessary tables on startup:

```bash
# Simply start the server - everything is auto-initialized
python server.py
```

**Output on first run:**
```
=============================================================
🚀 STARTING RESUME ATS SYSTEM
=============================================================
Initializing database and creating tables...
✓ Resume database initialized
✓ Job database initialized
✓ All services initialized successfully
✓ Database files created at: resume_database.db
🚀 Server ready to accept requests
```

### Manual Database Setup (Optional)
If you want to initialize databases separately:

```bash
python init_database.py
```

## Database Auto-Creation Features

✅ **Automatic Table Creation**: All tables created on server startup  
✅ **Index Creation**: Performance indexes automatically added  
✅ **Schema Validation**: Tables checked for proper structure  
✅ **Health Monitoring**: Database connection tested on startup  
✅ **Zero Configuration**: Works out of the box  

### Tables Created Automatically:

#### Resume Database (`resume_database.db`)
- **resumes** - Store processed resumes with embeddings
- **Indexes** - embedding_model, created_at

#### Job Database (same file)
- **job_postings** - Store job postings with embeddings  
- **Indexes** - skills_json, location, job_type

## API Endpoints

### Main Resume Processing
- `POST /upload-pdf` - **Main endpoint**: Upload resume, get ATS score + job matches
- `GET /resumes` - List all processed resumes
- `GET /resumes/<id>` - Get specific resume details

### ATS Analysis
- `POST /ats/analyze` - Analyze stored resume with ATS
- `POST /ats/score` - Calculate ATS score for resume data
- `POST /ats/match-jobs` - Find matching jobs for resume

### Job Management
- `POST /jobs/feed` - Upload CSV file with job postings
- `GET /jobs` - List all jobs
- `GET /jobs/<id>` - Get specific job
- `POST /jobs/search/skills` - Search jobs by skills
- `POST /jobs/search/similar` - Find similar jobs

### Background Processing
- `POST /process/<resume_id>` - Start background processing
- `GET /task/<task_id>` - Check task status
- `POST /score/batch` - Batch score resumes
- `POST /rank` - Rank resumes with custom weights

## Usage Examples

### Complete Resume Processing (Main Use Case)
```bash
curl -X POST -F "file=@resume.pdf" http://localhost:5000/upload-pdf
```

**Response includes:**
- Resume text extraction and NLP analysis
- Comprehensive ATS score breakdown
- Top 10 matching jobs with match percentages
- Improvement recommendations

### Feed Jobs from CSV
```bash
curl -X POST -F "file=@jobs.csv" http://localhost:5000/jobs/feed
```

### ATS Analysis Only
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"resume_id": 1}' \
  http://localhost:5000/ats/analyze
```

## CSV Format for Jobs

```csv
title,company,location,description,requirements,salary_min,salary_max,job_type,experience_level,posted_date
Senior Python Developer,TechCorp,San Francisco CA,Develop backend APIs...,Python, Django, AWS...,120000,180000,Full-time,Senior,2024-01-15
```

**Flexible column mapping:**
- `title`, `job_title`, `position`, `role`
- `company`, `company_name`, `employer`
- `description`, `job_description`, `details`
- `requirements`, `qualifications`, `skills_required`

## ATS Scoring Grades

| Score Range | Grade | Description |
|-------------|-------|-------------|
| 90-100% | A+ | Excellent resume, highly likely to pass ATS |
| 80-89% | A | Strong resume, good ATS compatibility |
| 70-79% | B+ | Good resume, minor improvements needed |
| 60-69% | B | Average resume, some improvements needed |
| 50-59% | C+ | Below average, significant improvements needed |
| 40-49% | C | Poor ATS compatibility |
| 30-39% | D | Very poor, major overhaul needed |
| Below 30% | F | Unlikely to pass any ATS |

## Job Match Levels

| Score Range | Match Level | Description |
|-------------|-------------|-------------|
| 80-100% | Excellent Match | Strong alignment, highly recommended |
| 60-79% | Good Match | Good fit, worth applying |
| 40-59% | Moderate Match | Some alignment, consider with caution |
| Below 40% | Poor Match | Low alignment, not recommended |

## Database Schema

### Resumes Table
```sql
resumes (
  id, filename, filepath, raw_text, extracted_text_preview,
  skills_json, keywords_json, persons_json, organizations_json,
  embedding_blob, embedding_dimension, embedding_model,
  created_at, updated_at
)
```

### Job Postings Table
```sql
job_postings (
  job_id, title, company, location, description, requirements,
  skills_json, keywords_json, embedding_blob, salary_min/max,
  job_type, experience_level, posted_date, source_file
)
```

## Frontend Integration

### Expected Response Format
```json
{
  "message": "Resume processed successfully with ATS analysis",
  "resume_data": {
    "filename": "resume.pdf",
    "extracted_text": "...",
    "nlp_analysis": {
      "SKILL": ["Python", "AWS", "Docker"],
      "KEYWORDS": ["software", "development", "api"]
    },
    "embedding": {"embedding": [...], "dimension": 384}
  },
  "ats_analysis": {
    "ats_scores": {
      "overall_score": 0.78,
      "ats_grade": "B+",
      "format_score": 0.8,
      "skills_score": 0.7,
      "experience_score": 0.8,
      "education_score": 0.6,
      "keyword_score": 0.7
    },
    "matching_jobs": [
      {
        "job": {...},
        "match_score": 0.85,
        "match_percentage": 85.0,
        "match_level": "Excellent Match",
        "similarity_score": 0.82,
        "skills_match_score": 0.88,
        "experience_match_score": 0.85
      }
    ],
    "recommendations": [
      "Add more technical skills relevant to target roles",
      "Quantify experience with specific achievements"
    ],
    "summary": {
      "ats_score": 0.78,
      "ats_grade": "B+",
      "total_matching_jobs": 5,
      "top_match_score": 85.0,
      "top_job_title": "Senior Python Developer"
    }
  }
}
```

## Production Considerations

- **Database**: Upgrade to PostgreSQL with pgvector for better performance
- **Caching**: Redis caching for frequently accessed data
- **Monitoring**: Add logging, metrics, and health checks
- **Security**: Authentication, rate limiting, file validation
- **Scalability**: Load balancing, horizontal scaling
- **ML Models**: Consider fine-tuning embedding models on resume data

## Error Handling

The system provides comprehensive error handling:
- **File Upload Errors**: Invalid format, size limits
- **Processing Errors**: PDF extraction failures, NLP errors
- **Database Errors**: Connection issues, constraint violations
- **ATS Scoring Errors**: Missing data, calculation failures
- **Job Matching Errors**: No jobs available, embedding failures

All errors return structured JSON responses with appropriate HTTP status codes.
