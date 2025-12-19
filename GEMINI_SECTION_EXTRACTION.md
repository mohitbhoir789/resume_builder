# Gemini-Powered Resume Section Extraction

## Overview

The resume ingestion system now uses **Google Gemini AI** to intelligently extract resume sections instead of relying on regex patterns. This provides:

✅ **Intelligent parsing** - Understands context and structure  
✅ **Robust extraction** - Works with various resume formats  
✅ **Automatic fallback** - Falls back to regex if Gemini fails  
✅ **Accurate embeddings** - Creates embeddings only from identified sections  

## How It Works

### 1. **Resume Upload**
You provide your resume via:
- PDF file path
- URL to PDF
- Plain text

### 2. **Gemini Section Extraction**
The system sends your resume to Google Gemini with a prompt to extract:
- **Experience** - Work history, employment details
- **Projects** - Portfolio projects, side projects
- **Skills** - Technical skills, languages, tools
- **Education** - Degrees, universities, schools
- **Certifications** - Certs, licenses, credentials

### 3. **Embeddings Creation**
For each extracted item:
- Create semantic embeddings using E5 or Hashing provider
- Store embeddings in local FAISS vector database
- Each embedding captures the meaning of that resume section

### 4. **Local Storage**
Everything is saved locally:
- Profile data (JSON)
- Embeddings (pickle)
- Metadata (JSON)

## Setup

### Step 1: Get Gemini API Key

1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key (free tier available)
3. Copy the key

### Step 2: Set API Key in Notebook

In the notebook, after cell 2, update:

```python
GEMINI_API_KEY = "YOUR_API_KEY_HERE"  # Replace with your actual key
```

Example:
```python
GEMINI_API_KEY = "AIzaSyDxXxXxXxXxXxXxXxXxXxXxXxXxXxXx"
```

### Step 3: Or Set via Environment

Alternatively, set it globally:

```bash
export GOOGLE_API_KEY="your-api-key-here"
```

## Usage

### Option 1: From PDF File
```python
# In notebook, update PDF_FILE_PATH
PDF_FILE_PATH = "/path/to/your/resume.pdf"
# Then run the cell
```

**Result:**
- Resume parsed with Gemini AI
- Sections automatically extracted
- Embeddings created and stored

### Option 2: From URL
```python
# In notebook, update PDF_URL
PDF_URL = "https://example.com/resume.pdf"
# Then run the cell
```

### Option 3: Plain Text
```python
# In notebook, paste your resume in RESUME_TEXT
RESUME_TEXT = """
Your resume text here...
"""
# Then run the cell
```

## Embedding Creation Process

For each extracted item (e.g., each job, project, skill):

1. **Text**: "Senior Engineer at TechCorp (2020-2024) led team of 5..."
2. **Embedding**: [0.234, -0.567, 0.891, ...] (1024 dimensions)
3. **Storage**: Saved in FAISS vector store + pickle file
4. **Metadata**: Attached with section info, recency, seniority

### Embedding Dimensions
- **Provider**: E5 (sentence-transformers) or Hashing
- **Dimensions**: 1024
- **Type**: Dense vector representation of resume content

### Metadata Attached
```json
{
  "section": "experience",
  "title": "Senior Engineer at TechCorp",
  "recency_score": 0.95,
  "seniority": "mid",
  "id": "sha256-hash"
}
```

## Fallback to Regex

If Gemini is unavailable or fails:
- System automatically falls back to regex-based extraction
- Works with basic resume structure (headers: Experience, Projects, etc.)
- Less robust but functional

## Profile Data Storage

After ingestion, you get:

```
profile_cache/
├── my_profile_profile.json          # Resume data
├── my_profile_embeddings.pkl        # Vector embeddings
└── my_profile_metadata.json         # Ingestion metadata
```

### Profile JSON Structure
```json
{
  "experience": ["Job 1", "Job 2", ...],
  "projects": ["Project 1", ...],
  "skills": ["Python", "Machine Learning", ...],
  "education": ["MS in Data Science", ...],
  "certifications": ["AWS Certified", ...]
}
```

### Metadata JSON
```json
{
  "profile_name": "my_profile",
  "ingest_type": "text",
  "sections": ["experience", "projects", "skills", "education"],
  "chunks_created": 15,
  "embedding_provider": "E5EmbeddingProvider",
  "timestamp": 1702920000
}
```

## Usage in Resume Generator

Once profiles are ingested and embeddings created:

1. **Open web app**: `http://localhost:3000`
2. **Enter profile name**: `my_profile`
3. **Fill job details**: Job title, company, etc.
4. **Generate**: System retrieves relevant resume content using embeddings
5. **Download**: Get tailored resume PDF

### How Embeddings Help
- **Semantic search**: Find relevant resume content for job
- **Relevance scoring**: Rank which skills/experience matter most
- **Fast retrieval**: FAISS provides sub-millisecond lookup
- **No training**: Pre-computed during ingestion

## Troubleshooting

### "No module named 'google.generativeai'"
Solution: Already installed by pip install command in cell 1

### "Invalid or no API key"
Solution: 
1. Get key from https://makersuite.google.com/app/apikey
2. Set `GEMINI_API_KEY` in notebook cell 3

### "Profile data is 0 after ingestion"
- Check: Did Gemini extract sections properly?
- Look at: Console output should show extracted sections
- Try: Use regex fallback by not setting API key

### "Chunks: 0 after ingestion"
- This is OK! Chunks are for embeddings
- Profile data contains actual extracted content
- Data is saved even if chunks are 0

## Benefits of Gemini Integration

1. **Context Understanding**: Gemini understands resume context
   - "Manager" in "Senior Project Manager" vs "Manager (part-time)"
   - Different meaning, different context

2. **Flexible Formats**: Works with any resume format
   - Traditional chronological
   - Functional resumes
   - Combination resumes
   - Hybrid formats

3. **Accurate Extraction**: Gets the right items
   - All experience entries
   - All projects
   - All skills and certifications
   - Complete education

4. **Better Embeddings**: More accurate semantic representations
   - Each item properly identified
   - Better for resume matching
   - Improved tailoring results

## Next Steps

1. ✅ Get Gemini API key
2. ✅ Set it in notebook
3. ✅ Run notebook to ingest resume
4. ✅ See profile data populated
5. ✅ Generate tailored resumes using web app

## Support

- **Gemini Docs**: https://ai.google.dev/docs
- **Free Tier**: 60 requests/minute
- **API Status**: https://status.ai.google.dev/

