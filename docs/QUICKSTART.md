# De-Identification App - Quick Start Guide

A local-only tool for removing personally identifiable information (PII) from research data. All processing happens on your computer — your data never leaves your machine.

## Table of Contents

- [Installation Options](#installation-options)
- [Option 1: Docker (Recommended)](#option-1-docker-recommended)
- [Option 2: Using uv (Alternative)](#option-2-using-uv-alternative)
- [Using the App](#using-the-app)
- [Troubleshooting](#troubleshooting)

---

## Installation Options

| Method | Best For | Requirements |
|--------|----------|--------------|
| **Docker** | Non-technical users | Docker Desktop |


---

## Docker

Docker bundles everything needed to run the app, including the ~560MB language model. Once built, the app runs completely offline with no network access.

### Step 1: Install Docker Desktop

**Mac:**
1. Download Docker Desktop from https://www.docker.com/products/docker-desktop/
2. Open the downloaded `.dmg` file
3. Drag Docker to Applications
4. Open Docker from Applications
5. Wait for Docker to start (whale icon in menu bar will stop animating)

**Windows:**
1. Download Docker Desktop from https://www.docker.com/products/docker-desktop/
2. Run the installer
3. Restart your computer if prompted
4. Open Docker Desktop
5. Wait for Docker to start (green "Running" status in the app)

**Linux:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io docker-compose
sudo systemctl start docker
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect
```

### Step 2: Run the App

**Mac/Linux:**
```bash
# Navigate to the app folder
cd deidentify-app

# Run the launcher script (first run takes 5-10 minutes to build)
./run.sh
```

**Windows:**
```batch
# Navigate to the app folder
cd deidentify-app

# Double-click run.bat or run from Command Prompt:
run.bat
```

The app will automatically:
1. Check that Docker is installed and running
2. Build the Docker image (first time only, ~5-10 minutes)
3. Create output directories
4. Start the container with network isolation
5. Open your browser to http://localhost:8501

### Step 3: Use the App

Once the browser opens:
1. Upload your data file (CSV, Excel, or text)
2. Configure which columns to process
3. Select which types of PII to detect
4. Choose anonymization strategies
5. Preview the results
6. Export the de-identified file and audit log

### Stopping the App

```bash
docker stop deidentify-app
```

### Rebuilding (After Updates)

```bash
./run.sh --rebuild    # Mac/Linux
run.bat --rebuild     # Windows
```

---

## Using the App

### File Upload

The app accepts:
- **CSV files** (.csv)
- **Excel files** (.xlsx, .xls)
- **Text files** (.txt)

### Column Configuration

After uploading, configure how each column should be processed:

| Type | Description | Use For |
|------|-------------|---------|
| **Skip** | Don't process | Record IDs, dates you want to keep |
| **Structured** | Regex patterns only | Email columns, phone columns |
| **Free Text** | Full NER + regex | Notes, comments, descriptions |
| **Direct Identifier** | Always fully redact | SSN columns, known PII fields |

### Entity Types

Select which types of PII to detect:
- Names (PERSON)
- Locations (LOCATION)
- Dates (DATE_TIME)
- Phone numbers (PHONE_NUMBER)
- Email addresses (EMAIL_ADDRESS)
- Social Security Numbers (US_SSN)
- Medical record numbers (custom)
- And more...

### Anonymization Strategies

Choose how to handle each entity type:

| Strategy | Result | Use When |
|----------|--------|----------|
| **Redact** | `[REDACTED]` | Maximum privacy |
| **Type Tag** | `[PERSON_1]` | Preserve entity counts |
| **Mask** | `J*** S****` | Keep partial info |
| **Hash** | `a1b2c3d4` | Link records together |
| **Fake** | `John Smith` → `Jane Doe` | Preserve readability |

### Confidence Threshold

Adjust how aggressively the app detects PII:
- **0.3-0.5 (Aggressive)**: Catches more, may have false positives
- **0.7 (Moderate)**: Good balance (default)
- **0.8-1.0 (Conservative)**: Fewer false positives, may miss some

For IRB submissions, we recommend 0.5 with manual review.

### Export

Download:
- **De-identified file**: Same format as input
- **Audit log (JSON)**: Documents what was detected and changed (required for IRB)

---

## Troubleshooting

### Docker Issues

**"Docker is not installed"**
- Install Docker Desktop: https://www.docker.com/products/docker-desktop/

**"Docker is not running"**
- Mac: Open Docker from Applications
- Windows: Open Docker Desktop
- Linux: `sudo systemctl start docker`

**Build fails with network error**
- Docker needs internet during build to download dependencies
- After building, the app runs fully offline

**Out of memory during build**
- Increase Docker memory: Docker Desktop → Settings → Resources → Memory → 4GB+

### App Issues

**Browser shows "Unable to connect"**
- Wait a few seconds for the app to start
- Check if container is running: `docker ps`
- Check logs: `docker logs deidentify-app`

**File upload fails**
- Ensure file is CSV, Excel, or text format
- Check file isn't corrupted
- Try a smaller file first

**Low detection accuracy**
- Lower the confidence threshold
- Ensure columns are set to "Free Text" mode
- The SpaCy model works best with English text

---

## File Locations

| Purpose | Location |
|---------|----------|
| Input data | `deidentify-app/data/` |
| De-identified output | `deidentify-app/output/` |
| Audit logs | `deidentify-app/audit/` |
| Sample data | `deidentify-app/data/sample/` |

---

## Security Notes

- All processing happens locally on your computer
- The Docker container runs with `--network none` (no internet access)
- Your data is never uploaded anywhere
- Audit logs document all changes for IRB compliance
- Audit logs never contain the original PII text

---

## Getting Help

If you encounter issues:
1. Check the [Troubleshooting](#troubleshooting) section above
2. Review the audit log for detection details
3. Contact your research computing support team
