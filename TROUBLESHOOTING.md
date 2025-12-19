# 🔧 Troubleshooting Guide

## Common Issues & Solutions

### 🔴 Profile Not Found

**Error**: "Profile not found: my_profile"

**Solutions**:
1. Check spelling of profile name
   ```bash
   # View saved profiles
   ls profile_cache/*_metadata.json
   ```

2. Make sure notebook completed successfully
   ```bash
   # Re-run ingest cell in notebook
   jupyter notebook ingest_profile.ipynb
   ```

3. Verify profile_cache directory exists
   ```bash
   ls -la profile_cache/
   ```

---

### 🔴 Backend Won't Start

**Error**: "Address already in use: ('0.0.0.0', 8000)"

**Solutions**:
1. Kill existing process
   ```bash
   lsof -ti:8000 | xargs kill -9
   ```

2. Use different port
   ```bash
   # Edit start.sh and change 8000 to 8001
   ```

3. Wait a minute and try again
   ```bash
   sleep 60
   ./start.sh
   ```

---

### 🔴 Frontend Won't Load

**Error**: "Connection refused" at http://localhost:3000

**Solutions**:
1. Check if services are running
   ```bash
   # Check processes
   ps aux | grep "node\|uvicorn"
   ```

2. Start services
   ```bash
   ./start.sh
   ```

3. Clear browser cache
   ```bash
   # Cmd+Shift+Delete on Chrome/Firefox
   # Or use incognito/private window
   ```

---

### 🔴 Notebook Import Error

**Error**: "ModuleNotFoundError: No module named 'app'"

**Solutions**:
1. Check working directory
   ```bash
   # Must run from project root
   cd /Users/mohitbhoir/Git/resume_builder
   jupyter notebook ingest_profile.ipynb
   ```

2. Install missing packages
   ```bash
   # Activate venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Restart Jupyter kernel
   - Click: Kernel → Restart → Clear Outputs

---

### 🔴 Embeddings Won't Load

**Error**: "Embeddings not found for profile: my_profile"

**Solutions**:
1. Verify file exists
   ```bash
   ls profile_cache/my_profile_embeddings.pkl
   ```

2. Check file permissions
   ```bash
   chmod 644 profile_cache/my_profile_embeddings.pkl
   ```

3. Re-create embeddings
   ```bash
   # Run notebook ingest again
   jupyter notebook ingest_profile.ipynb
   ```

---

### 🔴 PDF Generation Fails

**Error**: "PDF render failed (pages=0)"

**Solutions**:
1. Check if LaTeX is installed
   ```bash
   # macOS
   which pdflatex
   ```

2. Install MacTeX if missing
   ```bash
   # macOS - install via Homebrew
   brew install basictex
   ```

3. Verify pdfinfo is available
   ```bash
   which pdfinfo
   ```

---

### 🔴 Slow Resume Generation

**Cause**: First generation is slow (30-60 seconds)

**Solutions**:
1. This is normal! 
   - Keyword extraction
   - Semantic mapping
   - LaTeX compilation
   - Are all computationally intensive

2. Subsequent generations with same profile are faster

3. Profile caching reduces overhead

---

### 🔴 API Returns 500 Error

**Error**: "Internal Server Error" response from backend

**Solutions**:
1. Check backend logs
   ```bash
   # Look at terminal running ./start.sh
   ```

2. Common causes:
   - Profile name typo
   - Missing job description
   - Invalid profile format

3. Verify profile format
   ```bash
   cat profile_cache/my_profile_profile.json
   ```

---

### 🔴 Git Issues After Changes

**Issue**: How to add changes to git?

**Solutions**:
```bash
# Add modified files
git add frontend/ backend/ start.sh

# Add new documentation
git add *.md IMPLEMENTATION_CHECKLIST.md

# Ignore profile cache
# (Already in .gitignore)
git add -A
git commit -m "Move embeddings to notebook, simplify frontend"

# Push changes
git push origin main
```

---

## Debugging Steps

### 1. Check System Status
```bash
# Are services running?
ps aux | grep "node\|uvicorn"

# Can you reach frontend?
curl http://localhost:3000

# Can you reach backend?
curl http://localhost:8000/health

# Are profiles saved?
ls -la profile_cache/
```

### 2. Check Logs

**Frontend errors**: Browser console (F12 → Console tab)

**Backend errors**: Terminal running `./start.sh`

**Notebook errors**: Jupyter cell output

### 3. Common Log Messages

| Message | Meaning | Action |
|---------|---------|--------|
| `"Waiting for application startup"` | Backend loading | Wait 5-10s |
| `"StatReload detected changes"` | File changed, reloading | Wait for "complete" |
| `"ERR_CONNECTION_REFUSED"` | Backend not running | Run `./start.sh` |
| `"ModuleNotFoundError"` | Missing import | Install packages |
| `"Profile not found"` | Profile doesn't exist | Run notebook |

---

## Reset Everything

If something is seriously broken:

```bash
# 1. Stop all services
# Press Ctrl+C in all terminals

# 2. Kill any hanging processes
pkill -f uvicorn
pkill -f "next dev"

# 3. Clear artifacts
rm -rf artifacts/*

# 4. Optional: Reset profiles
rm -rf profile_cache/*

# 5. Start fresh
./start.sh

# 6. Re-ingest if needed
jupyter notebook ingest_profile.ipynb
```

---

## Performance Tips

### Optimize Profile Creation
```bash
# Choose plaintext input (fastest)
# PDF parsing is slower
# URL download adds time
```

### Optimize Resume Generation
```bash
# Keep job descriptions focused
# Shorter = faster processing
# ~500 words is ideal
```

### Optimize System
```bash
# Use SSD (not HDD)
# Close other applications
# Ensure sufficient RAM (4GB+ recommended)
```

---

## Getting Help

### Documentation Files
- `PROFILE_MANAGEMENT.md` - Usage guide
- `IMPLEMENTATION_SUMMARY.md` - Technical details
- `ARCHITECTURE.md` - System architecture
- `CHANGES_SUMMARY.md` - What changed

### Quick Commands
```bash
# View profiles
ls profile_cache/*_metadata.json

# Check services
ps aux | grep "node\|uvicorn"

# Test backend
curl http://localhost:8000/health

# View logs
tail -f /tmp/resume_builder.log  # If using logging
```

### Contact/Report Issues
- Check GitHub issues
- Review logs carefully
- Verify all files exist
- Confirm paths are correct

---

## FAQ

**Q: Can I have multiple profiles?**
A: Yes! Run the notebook multiple times with different names.

**Q: Will embeddings work offline?**
A: Yes, completely offline after initial training.

**Q: Can I edit saved profiles?**
A: Yes, manually edit the JSON files in `profile_cache/`

**Q: How large can profiles be?**
A: No limit, tested up to 50+ page resumes.

**Q: Do I need an API key?**
A: Only for LLM features (extraction fallback).

**Q: Can I share profiles?**
A: Yes, copy `profile_cache/` between machines.

**Q: How do I backup profiles?**
A: Run `cp -r profile_cache profile_cache_backup`

**Q: Can I delete old profiles?**
A: Yes, delete the three files (json, pkl, metadata).

---

## Emergency Recovery

### Lost All Profiles
```bash
# Check if .pkl files are recoverable
find . -name "*.pkl" -type f

# Or re-ingest from source
jupyter notebook ingest_profile.ipynb
```

### Corrupted Profile
```bash
# Delete all three files
rm profile_cache/bad_profile_*

# Re-ingest
jupyter notebook ingest_profile.ipynb
```

### Won't Start Anymore
```bash
# Nuclear option: reset everything
rm -rf profile_cache artifacts .next __pycache__

# Then start fresh
./start.sh
```

---

**Still stuck?** 
1. Check logs carefully
2. Review documentation
3. Try the troubleshooting steps above
4. Reset and start over if needed

Good luck! 🚀
