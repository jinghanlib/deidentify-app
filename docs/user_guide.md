# De-Identification Tool — User Guide

A practical guide for researchers to use the De-Identification Tool for protecting participant privacy in research data.

---

## Table of Contents

1. [What This Tool Does](#what-this-tool-does)
2. [Getting Started](#getting-started)
3. [Configuring Columns](#configuring-columns)
4. [Choosing What to Detect](#choosing-what-to-detect)
5. [Choosing How to Anonymize](#choosing-how-to-anonymize)
6. [Processing Your Data](#processing-your-data)
7. [Reviewing Results](#reviewing-results)
8. [Downloading Results](#downloading-results)
9. [Tips for Best Results](#tips-for-best-results)
10. [Troubleshooting](#troubleshooting)

---

## What This Tool Does

### Plain Language Explanation

This tool helps you **remove or mask personally identifiable information (PII)** from your research data before sharing or publishing it. Think of it as a smart "find and replace" that can detect names, addresses, phone numbers, and other sensitive information — then replace them with safe alternatives.

### Why It Matters for Research

- **IRB Compliance**: Most IRB protocols require de-identification before data sharing
- **HIPAA Safe Harbor**: This tool follows the 18-identifier standard for protected health information
- **Participant Protection**: Ensures participant privacy even if data is accidentally exposed

### Key Benefit: Local Processing

**All processing happens on your computer.** Your data never leaves your machine or gets sent to any cloud service. This is critical for sensitive research data.

---

## Getting Started

### Opening the App

1. Open your web browser (Chrome, Firefox, Safari, or Edge)
2. Navigate to: `http://localhost:8501`
3. You should see the De-Identification Tool interface

### Uploading Your Data

1. Click the **"Browse files"** button or drag your file into the upload area
2. Supported file types:
   - **CSV** (.csv) — Comma-separated values
   - **Excel** (.xlsx, .xls) — Microsoft Excel spreadsheets
   - **Text** (.txt) — Plain text files
3. After uploading, you'll see a preview of the first 5 rows

### Understanding the Preview

The preview shows you:
- Column names (headers)
- Sample data from each column
- Total number of rows loaded

This helps you verify the correct file was uploaded before processing.

---

## Configuring Columns

After uploading your file, you need to tell the tool how to handle each column. The tool will auto-detect column types, but you can adjust them.

### Column Type Options

| Type | When to Use | What Happens |
|------|-------------|--------------|
| **Skip** | Record IDs, row numbers, internal codes | Column is not processed at all |
| **Structured** | Email addresses, phone numbers, SSNs in dedicated columns | Uses pattern-matching only (faster, very accurate) |
| **Free Text** | Notes, comments, medical records, interview transcripts | Uses full AI analysis (slower, catches more) |
| **Direct Identifier** | Columns that should be completely removed (full name, SSN, etc.) | Entire column values are replaced with [REDACTED] |

### How to Change Column Types

1. Find the column in the configuration section
2. Click the dropdown next to the column name
3. Select the appropriate type
4. The change takes effect when you process the data

### Examples

- `participant_id` → **Skip** (you need this for linking records)
- `email` → **Structured** (emails have a predictable format)
- `medical_notes` → **Free Text** (contains sentences with names, dates, etc.)
- `ssn` → **Direct Identifier** (always fully remove)

---

## Choosing What to Detect

The sidebar contains checkboxes for each type of information the tool can detect.

### Entity Types Explained

| Entity Type | What It Finds | Examples |
|-------------|---------------|----------|
| **PERSON** | Names of people | "Sarah Johnson", "Dr. Smith" |
| **LOCATION** | Places, addresses | "123 Main St", "Boston, MA" |
| **DATE_TIME** | Dates (except year alone) | "March 15, 2024", "01/15/24" |
| **PHONE_NUMBER** | Phone and fax numbers | "(555) 123-4567" |
| **EMAIL_ADDRESS** | Email addresses | "user@example.com" |
| **US_SSN** | Social Security Numbers | "123-45-6789" |
| **US_DRIVER_LICENSE** | Driver's license numbers | State-specific formats |
| **URL** | Web addresses | "https://example.com" |
| **IP_ADDRESS** | Computer IP addresses | "192.168.1.1" |
| **MEDICAL_RECORD** | Medical record numbers | "MRN-12345" |
| **INSURANCE_ID** | Insurance policy numbers | "BCBS-445892" |
| **ACCOUNT_NUMBER** | Bank/financial accounts | Account numbers |

### Confidence Threshold

The slider controls how "sure" the tool needs to be before flagging something as PII.

| Setting | Threshold | When to Use |
|---------|-----------|-------------|
| **Aggressive** | 0.3-0.5 | When missing PII is worse than false alarms |
| **Moderate** | 0.5-0.7 | Good balance for most research data |
| **Conservative** | 0.7-1.0 | When you have lots of technical terms that might be confused for names |

**For IRB purposes**: We recommend **0.5** with manual review of flagged items.

---

## Choosing How to Anonymize

For each entity type, you can choose how detected items should be handled.

### Anonymization Strategies

| Strategy | Result | Best For |
|----------|--------|----------|
| **Redact** | `[REDACTED]` | Maximum privacy; when you don't need the structure |
| **Type Tag** | `[PERSON_1]`, `[PERSON_2]` | When you need to track how many unique entities exist |
| **Mask** | `S***h J*****n`, `***-**-6789` | When partial visibility helps review |
| **Hash** | `a1b2c3d4` | When same entity should always produce same code (linkage) |
| **Fake** | "John Smith" → "Michael Brown" | When you need realistic-looking data for demos |

### Strategy Selection

1. Choose a **default strategy** for all entity types
2. Override specific entity types if needed (e.g., use "Hash" for PERSON but "Redact" for SSN)

### Examples

**Original**: "Dr. Sarah Johnson called about patient's visit on 3/15/2024"

| Strategy | Result |
|----------|--------|
| Redact | "Dr. [REDACTED] called about patient's visit on [REDACTED]" |
| Type Tag | "Dr. [PERSON_1] called about patient's visit on [DATE_TIME_1]" |
| Mask | "Dr. S***h J*****n called about patient's visit on **/15/2024" |
| Hash | "Dr. a8f3c2d1 called about patient's visit on 7b2e9f4a" |

---

## Processing Your Data

### Starting the Process

1. Review your settings in the sidebar
2. Confirm your column configuration
3. Click the blue **"De-identify Data"** button
4. A spinner will appear while processing

### Processing Time

Processing time depends on:
- Number of rows in your data
- Number of columns marked as "Free Text"
- Complexity of the text content

**Typical times**:
- 100 rows, 2-3 text columns: ~10-30 seconds
- 1,000 rows, 2-3 text columns: ~1-5 minutes
- 10,000+ rows: Several minutes to tens of minutes

### Results Summary

After processing, you'll see a summary:
- Total number of records processed
- Total PII instances detected
- Breakdown by entity type

---

## Reviewing Results

After processing, four tabs appear: **Preview**, **Statistics**, **Review**, and **Export**.

### Preview Tab

Shows side-by-side comparison of original and de-identified text.

**Features**:
- **Color-coded highlighting**: Different PII types have different background colors
- **Row selector**: Navigate through your data
- **Column selector**: Choose which column to examine
- **Hover for details**: Hover over highlighted text to see entity type and confidence

**Color Legend** (displayed above the preview):
- Pink = PERSON
- Green = LOCATION
- Purple = DATE_TIME
- Blue = EMAIL_ADDRESS
- Red = US_SSN
- etc.

### Statistics Tab

Shows charts and numbers:
- Bar chart of detections by entity type
- Total detection count
- Which entity types were most common

### Review Tab (Manual Corrections)

The Review tab allows you to **correct detection errors** before exporting:

#### Rejecting False Positives

Detections with confidence **below your selected threshold** (from the sidebar) are shown as "uncertain". For example, if you set the threshold to 70%, detections with 40% or 60% confidence will appear here for review.

For each uncertain detection:
- Click **"Keep"** to confirm it should be de-identified
- Click **"Reject"** to mark it as NOT PII (will be left unchanged)
- Click **"Undo Reject"** to reverse a rejection

**Tip**: If you're seeing too many uncertain detections, try lowering your confidence threshold in the sidebar. If you're missing PII, try raising it.

#### Adding Missed PII

If the system missed PII that should be de-identified:

**Step 1: Select the cell**
- Choose the **row number** (1 = first data row)
- Choose the **column** containing the missed PII
- The cell content will be displayed for reference

**Step 2: Type the text to mark**
- Type or copy/paste the **exact text** you want to mark as PII
- The search only looks in the selected cell, not the entire dataset
- Search is **case-sensitive**: "Nancy" won't match "nancy"

**Step 3: Add as PII**
- Select the entity type (PERSON, PHONE_NUMBER, CUSTOM_ID, etc.)
- Click **"Add as [type]"** to add it

**Example**: If the system missed "Nancy" as a name:
1. Select Row 1, Column "notes"
2. The cell content appears: "I met with Nancy at the clinic..."
3. Type `Nancy` in the search box
4. It shows: Found 1 occurrence of "Nancy"
5. Select `PERSON` as the entity type
6. Click "Add as PERSON"

**Important**: This searches only the **selected cell**, not the entire dataset. To find PII in other cells, change the row and column selection.

#### Custom Entity Types

You can define your own entity types for study-specific identifiers:

1. Expand "Define Custom Entity Types"
2. Enter a type name (e.g., `STUDY_ID`, `SITE_CODE`, `PARTICIPANT_ID`)
3. Optionally add a description (e.g., "6-digit participant identifier")
4. Click "Add Custom Type"

Your custom types will then appear in the entity type dropdown when adding missed PII.

**Use cases for custom types:**
- Study-specific participant IDs (e.g., "SUBJ-001")
- Site or location codes
- Internal reference numbers
- Any identifier format unique to your research

#### Applying Corrections

After marking your corrections:
1. Review the **Corrections Summary** showing pending changes
2. Click **"Apply Corrections & Reprocess"**
3. The data will be reprocessed with your corrections
4. Check the Preview tab to verify results

**Note**: Corrections are tracked in the audit log for IRB compliance.

### What to Look For During Review

1. **False positives**: Common words incorrectly flagged as names
2. **Missed PII**: Names or other PII that weren't detected
3. **Context issues**: Ensure redactions make sense in context

---

## Downloading Results

### Available Downloads

The **Export** tab provides three download buttons:

| File | Format | Purpose |
|------|--------|---------|
| **De-identified Data** | CSV or Excel | Your cleaned data ready for sharing |
| **Audit Log** | JSON | Technical record of all detections (for IRB) |
| **IRB Summary** | Markdown | Human-readable summary for IRB documentation |

### De-identified Data File

- Same format as your input (CSV → CSV, Excel → Excel)
- Contains all rows and columns
- PII replaced according to your settings

### Audit Log (JSON)

The audit log documents:
- When processing occurred
- What settings were used
- What was detected and where
- What action was taken for each detection

**Important**: The audit log contains position and length information but **never** the original PII text.

### IRB Summary (Markdown)

A human-readable document you can include in IRB documentation:
- De-identification methodology
- Settings used
- Summary statistics
- Can be opened in any text editor or Markdown viewer

---

## Tips for Best Results

### Before You Start

1. **Remove unnecessary columns first**: Delete any columns you don't need before uploading
2. **Know your data**: Review a sample of your data to understand what PII it might contain
3. **Back up your original**: Always keep a secure copy of the original data

### Optimal Settings

1. **Start with Moderate threshold (0.5-0.7)**, review results, then adjust
2. **Mark known PII columns as Direct Identifier**: This ensures they're always fully redacted
3. **Use Free Text for narrative fields**: Notes, comments, and transcripts need full analysis

### Review Process

1. **Sample before processing full dataset**: Test on a small subset first
2. **Check the Preview tab thoroughly**: Look at multiple rows across different parts of your data
3. **Pay attention to professional titles**: "Dr.", "Prof.", etc. might not always trigger name detection
4. **Check for indirect identifiers**: Unique combinations (rare job + location) might identify someone

### Using the Review Tab

**Before downloading**, use the Review tab to correct any issues:
1. Reject false positives (words incorrectly flagged as PII)
2. Add missed PII using the position helper
3. Click "Apply Corrections & Reprocess"
4. All corrections are automatically documented in the audit log

### When to Manually Edit (After Download)

If you discover additional issues after downloading:
1. Download the de-identified file
2. Open in Excel or your preferred editor
3. Find and replace the remaining PII
4. Document the manual changes for your IRB

---

## Troubleshooting

### Common Issues

#### "Error reading file"
- **Cause**: File format issue or corruption
- **Fix**: Re-save your file as CSV (most compatible format)

#### Processing is very slow
- **Cause**: Large file or many Free Text columns
- **Fix**:
  - Mark more columns as "Skip" or "Structured" if possible
  - Process in smaller batches

#### Names not being detected
- **Cause**: Unusual name formats or non-English names
- **Fix**:
  - Lower the confidence threshold
  - Mark the column as "Direct Identifier" if it only contains names

#### Too many false positives
- **Cause**: Common words being flagged as entities
- **Fix**: Raise the confidence threshold to 0.7 or higher

#### Excel file won't upload
- **Cause**: Password protection or macros
- **Fix**: Save as a new .xlsx file without protection

### Getting Help

If you encounter issues not covered here:
1. Note the exact error message
2. Note what file type you're using and approximate size
3. Contact your technical support team

---

## Quick Reference Card

```
COLUMN TYPES
  Skip            → Don't touch (IDs, codes)
  Structured      → Pattern-only (emails, phones)
  Free Text       → Full AI analysis (notes, transcripts)
  Direct ID       → Always [REDACTED]

CONFIDENCE THRESHOLD
  0.3-0.5  Aggressive (catches more, more false positives)
  0.5-0.7  Moderate (balanced)
  0.7-1.0  Conservative (fewer false positives, might miss some)

STRATEGIES
  Redact    → [REDACTED]
  Type Tag  → [PERSON_1], [PERSON_2]...
  Mask      → S***h J*****n
  Hash      → a1b2c3d4 (consistent)
  Fake      → Realistic replacement

REVIEW TAB (MANUAL CORRECTIONS)
  Uncertain detections  → Keep or Reject false positives
  Add missed PII        → Select row/col, type text, click Add
  Custom entity types   → Define study-specific identifiers

NAVIGATION (after processing)
  1. Preview     → See before/after comparison
  2. Statistics  → View detection summary
  3. Review      → Correct errors (reject/add PII)
  4. Export      → Download files

OUTPUTS
  1. De-identified data (CSV/Excel)
  2. Audit log (JSON) - for records
  3. IRB summary (Markdown) - for documentation
```

---

*Last updated: 2025*
