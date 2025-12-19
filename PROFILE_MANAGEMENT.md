# Resume Ingestion & Profile Management Guide

This guide explains how to use the new profile-based workflow for the Resume Builder.

## Overview

The new architecture eliminates real-time embeddings training from the frontend. Instead:

1. **Pre-ingest** your resume once using the Jupyter notebook (`ingest_profile.ipynb`)
2. **Store** the profile and embeddings locally in `profile_cache/`
3. **Generate** resumes on-demand via the web UI by referencing your saved profile

This approach offers:
- ✅ No embedding training overhead in the UI
- ✅ Fast resume generation (instant profile loading)
- ✅ Support for multiple resume profiles
- ✅ Local storage (no external dependencies)

## Step 1: Pre-Ingest Your Resume

### Using Jupyter Notebook

```bash
jupyter notebook ingest_profile.ipynb
```

The notebook provides three options:

#### Option 1: From PDF File Path
```python
PDF_FILE_PATH = "/Users/yourname/Documents/resume.pdf"
```

#### Option 2: From URL
```python
PDF_URL = "https://example.com/my-resume.pdf"
```

#### Option 3: From Plaintext
```python
RESUME_TEXT = """
Experience
- Job 1: Description
- Job 2: Description

Projects
- Project 1: Description

Skills
- Python, JavaScript, React

Education
- Bachelor's in Computer Science
"""
```

### Save Your Profile

The notebook will:
1. Extract sections from your resume
2. Train embeddings locally
3. Save files to `profile_cache/`:
   - `my_profile_profile.json` — Structured resume data
   - `my_profile_embeddings.pkl` — Trained embeddings
   - `my_profile_metadata.json` — Profile metadata

**Note**: Replace `my_profile` with your custom profile name if desired.

## Step 2: View Saved Profiles

Use the notebook's "View Saved Profiles" cell to see all available profiles:

```
📁 Available saved profiles:

📄 my_profile
   Type: text
   Sections: experience, projects, skills, education
   Chunks: 12

📄 senior_engineer_profile
   Type: pdf
   Sections: experience, projects, skills, education, certifications
   Chunks: 25
```

## Step 3: Generate Resumes

### Launch the Web UI

```bash
./start.sh
```

Open http://localhost:3000

### Generate a Resume

1. **Select Profile**: Enter your profile name (default: `my_profile`)
2. **Enter Job Details**:
   - Job Title
   - Company (optional)
   - Location (optional)
   - Job Description
3. **Click Generate Resume**
4. **Download PDF** with ATS-optimized content

## Managing Multiple Profiles

Create profiles for different career paths:

```bash
jupyter notebook ingest_profile.ipynb
```

### Example: Multiple Profiles

```
profile_cache/
├── junior_dev_profile.json
├── junior_dev_embeddings.pkl
├── senior_dev_profile.json
├── senior_dev_embeddings.pkl
├── data_science_profile.json
└── data_science_embeddings.pkl
```

Then in the UI:
- Enter `junior_dev` to generate junior-focused resume
- Enter `senior_dev` to generate senior-focused resume
- Enter `data_science` to generate data science-focused resume

## File Structure

```
project_root/
├── ingest_profile.ipynb           # Notebook for profile creation
├── profile_cache/                 # Local profile storage
│   ├── my_profile_profile.json
│   ├── my_profile_embeddings.pkl
│   └── my_profile_metadata.json
├── frontend/                       # Web UI
├── backend/                        # API server
│   ├── app/
│   │   ├── storage/
│   │   │   ├── profile_loader.py   # NEW: Profile loader
│   │   │   └── ...
│   │   └── services/
│   │       ├── orchestrator.py     # UPDATED: Uses ProfileLoader
│   │       └── ...
│   └── ...
└── start.sh                        # Single command to start both services
```

## API Changes

The resume generation endpoint now accepts `profile_name`:

### Old Way (Deprecated)
```json
{
  "job": { "title": "...", "description": "..." },
  "profile": { "experience": [], "projects": [], ... }
}
```

### New Way (Recommended)
```json
{
  "job": { "title": "...", "description": "..." },
  "profile_name": "my_profile"
}
```

## Troubleshooting

### Profile Not Found

If you see "Profile not found: xyz":
1. Check profile name spelling
2. Run notebook's "View Saved Profiles" cell
3. Re-run the ingest cell to create the profile

### Embeddings Load Error

If embeddings fail to load:
1. Ensure `profile_cache/` directory exists
2. Verify `.pkl` file exists for your profile
3. Re-ingest the profile using the notebook

### Multiple Profiles Not Showing

The UI doesn't show a list of profiles. To use a different profile:
1. Enter the profile name in the input field
2. Ensure it exists in `profile_cache/`
3. Generate as normal

## Advanced: Custom Profile Names

In the notebook, change this line:
```python
profile_name = "my_profile"  # Change this
```

To:
```python
profile_name = "my_custom_name"
```

Then save and use `my_custom_name` in the UI.

## Backup & Migration

To backup profiles:
```bash
cp -r profile_cache profile_cache_backup
```

To share profiles with teammates:
1. Export `profile_cache/` directory
2. Share the files
3. Place in their `profile_cache/` directory

## Tips

1. **Use descriptive names**: `senior_backend_dev`, `data_science_2025`
2. **Keep one active profile**: Use `my_profile` for quick iteration
3. **Archive old profiles**: Rename to `_archived_old_profile` to keep but not use
4. **Test profile quality**: Generate a few resumes to verify it's working
