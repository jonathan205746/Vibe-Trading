---
name: doc-reader
description: Read PDF documents (papers, annual reports, research reports), automatically extracting text pages and applying OCR to image/scanned pages. Use the `read_document` tool.
category: tool
---
# PDF Document Reading

## Purpose

Read the full text of PDF documents and automatically handle two page types:
- **Text pages** (most papers and digital reports) → extracted directly in milliseconds
- **Image / scanned pages** (annual report charts, scanned research reports) → OCR recognition with Chinese and English support

Applicable to PDF documents such as papers, annual reports, research reports, announcements, and contracts.

## Usage

**Call the `read_document` tool directly (do not use bash to write a Python script):**

```
read_document(file_path="uploads/paper.pdf")
read_document(file_path="uploads/annual_report.pdf", pages="1-10")
read_document(file_path="uploads/research.pdf", pages="1,3,15-20")
```

**Forbidden**: do not run a Python script from bash to read PDFs. Call the tool directly.

## Return Format

```json
{
  "status": "ok",
  "file": "paper.pdf",
  "total_pages": 45,
  "pages_read": 45,
  "ocr_pages": 3,
  "char_count": 52000,
  "truncated": true,
  "text": "--- Page 1 ---\n...\n--- Page 5 [OCR] ---\n..."
}
```

- `ocr_pages`: number of pages recognized via OCR (image / scanned pages)
- `truncated`: content is truncated when it exceeds 15000 characters
- `[OCR]` indicates that the page content was obtained via image recognition

## Typical Workflows

### Paper Summary
```
1. read_document(file_path="paper.pdf")  → get the full text
2. Analyze the text and extract the abstract, methodology, and conclusion
3. Output the summary
```

### Annual Report Analysis
```
1. read_document(file_path="annual_report.pdf", pages="1-5")  → read the summary first
2. Determine the key sections from the summary
3. read_document(file_path="...", pages="15-25")  → read the financial-data section
4. Extract key metrics
```

### Research Report Review
```
1. read_document(file_path="research.pdf")  → full text
2. Extract the core thesis, target price, and risk factors
```

## Notes

- Content longer than 15000 characters will be truncated. For long documents, read them in chunks with the `pages` parameter
- OCR pages are slower (about 1-3 seconds per page), while pure text pages are processed in milliseconds
- OCR for charts and tables inside images may be imperfect, so complex tables should be checked manually
- Only PDF format is supported
