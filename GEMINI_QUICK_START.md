# Quick Start: Gemini-Powered Resume Ingestion

## 30-Second Setup

### 1. Get Free API Key (1 minute)
```bash
# Go to this link in your browser:
https://makersuite.google.com/app/apikey

# Click "Create API Key" → Copy it
```

### 2. Update Notebook (30 seconds)
Open `ingest_profile.ipynb`, go to **cell 3**, and replace:
```python
GEMINI_API_KEY = "YOUR_API_KEY_HERE"
```

With your actual key:
```python
GEMINI_API_KEY = "AIzaSyDxXxXxXxXxXxXxXxXxXxXxXxXxXxXx"
```

### 3. Run Notebook (2 minutes)
```
Cell 1: pip install... ✅
Cell 2: Setup ✅  
Cell 3: Set API key ✅
Cell 5 or 6 or 8: Choose ingest method → Run ✅
Cell 10: Save profile ✅
```

### 4. View Results
Run **cell 11** to see all extracted profile data:
```
✅ Loaded profile: my_profile

Experience (3 items):
  1. Community Dreams Foundation | Data Science Intern...
  2. Beats by Dre | Data Science & Consumer Insights...
  3. Amdocs, India | Software Development Engineer...

Projects (3 items):
  1. Movie Recommendation Chatbot...
  ...

Skills (50+ items):
  1. Python
  2. Java
  3. JavaScript
  ...

Education (2 items):
  1. University of Connecticut - MS Data Science
  2. University of Mumbai - BE Electronics
```

## What Happens Under the Hood

### Without API Key (Regex Fallback)
- Pattern matching for "Experience", "Skills", etc.
- May miss items or extract incorrectly
- ⚠️ Profile data might be empty

### With API Key (Gemini AI)
1. Send resume to Gemini: "Extract these sections..."
2. Gemini analyzes and returns JSON
3. All items extracted accurately
4. Create embeddings for each item
5. Save locally (no cloud storage)

## Free Tier Limits

✅ **60 requests per minute** (enough for testing)  
✅ **Free tier available** (no credit card required)  
✅ **No usage limits** (just rate limited)

## Three Ways to Provide Resume

### Option A: PDF File Path
```python
PDF_FILE_PATH = "/Users/you/resume.pdf"
# Run cell 5
```

### Option B: URL
```python
PDF_URL = "https://example.com/my-resume.pdf"
# Run cell 7
```

### Option C: Plaintext
```python
RESUME_TEXT = """
Your Name
Email | Phone
...resume content...
"""
# Run cell 9
```

## Common Issues

### "Profile data is 0"
Usually means Gemini couldn't extract sections. Check:
1. Is API key set correctly?
2. Is resume text properly formatted?
3. Try regex fallback (delete API key)

### "Invalid JSON"
Gemini's response wasn't valid JSON. Happens occasionally.
Fix: Just re-run the cell (retry)

### "429 - Rate limited"
Free tier limit (60/min). Wait a minute, try again.

### "Unauthorized - invalid API key"
Copy key again from: https://makersuite.google.com/app/apikey

## After Setup: Using Profiles

Once you have a saved profile, you can:

```bash
# 1. Start the app
./start.sh

# 2. Open http://localhost:3000

# 3. Enter profile name (e.g., "my_profile")

# 4. Fill in job details

# 5. Generate resume (automatically tailored!)
```

The system uses embeddings to find the most relevant experience, skills, and projects for each job!

## Files Created

After ingestion:
```
profile_cache/
├── my_profile_profile.json          # Your extracted resume data
├── my_profile_embeddings.pkl        # 1024-dim vectors for each item
└── my_profile_metadata.json         # Ingestion details
```

All stored locally - no cloud upload!

## Advanced: Multiple Profiles

```python
# For different profiles:
profile_name = "data_science_role"  # Cell 10
# OR
profile_name = "swe_role"  # Cell 10

# Then run cells 10-11 for each
```

View all profiles:
```python
# Run cell 11 to see all available profiles
```

## Next: Generate Resumes

See `PROFILE_MANAGEMENT.md` for complete usage guide.

---

**Ready?** 
1. Get API key: https://makersuite.google.com/app/apikey
2. Open `ingest_profile.ipynb`
3. Update cell 3 with your key
4. Run the cells!
