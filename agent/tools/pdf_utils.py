import os
import subprocess
import pymupdf  # PyMuPDF is faster than pdfplumber for raw text
import logging

logger = logging.getLogger(__name__)

def extract_text_with_ocr_fallback(pdf_path: str) -> str:
    """
    Logic:
    1. Try standard extraction (PyMuPDF).
    2. If text is too short/empty (image-based PDF), run OCR via OCRmyPDF.
    3. Re-extract from the OCR'd file.
    4. Return text or raise error.
    """
    # Step 1: Standard Extraction
    text = ""
    try:
        doc = pymupdf.open(pdf_path)
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        logger.error(f"Initial PDF read failed: {e}")

    # Step 2: Check if it's likely an image (less than 50 chars)
    if len(text.strip()) < 50:
        print(f"🔍 No text found in {os.path.basename(pdf_path)}. Running OCR...")
        
        # Temporary path for OCR output
        ocr_pdf_path = pdf_path.replace(".pdf", "_searchable.pdf")
        
        try:
            # We use subprocess to call OCRmyPDF (cleaner than the API for CLI tools)
            # --skip-text: only OCR pages that don't have text
            # --deskew: straightens crooked scans (common in Kaggle sets)
            subprocess.run([
                "ocrmypdf", 
                "--skip-text", 
                "--deskew", 
                pdf_path, 
                ocr_pdf_path
            ], check=True, capture_output=True)

            # Step 3: Re-extract from the new file
            text = ""
            doc = pymupdf.open(ocr_pdf_path)
            for page in doc:
                text += page.get_text()
            doc.close()
            
            # Optional: Clean up OCR file to save space
            if os.path.exists(ocr_pdf_path):
                os.remove(ocr_pdf_path)

        except subprocess.CalledProcessError as e:
            print(f"❌ OCR failed for {pdf_path}: {e.stderr.decode()}")
            return ""
        except Exception as e:
            print(f"❌ Unexpected error during OCR: {e}")
            return ""

    # Step 4: Final Validation
    if len(text.strip()) < 10:
        raise ValueError(f"Even OCR could not retrieve data from {pdf_path}. File might be corrupted or blank.")

    return text.strip()