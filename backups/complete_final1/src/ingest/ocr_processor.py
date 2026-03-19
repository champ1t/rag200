
import os
import sys
import logging

try:
    import pytesseract
    from PIL import Image
    import io
except ImportError:
    # If dependencies missing, we provide stub
    pass

class OCRProcessor:
    """
    OCR Processor using Tesseract (via pytesseract).
    Handles extracting text from image bytes/files.
    """
    def __init__(self, lang: str = "thi+eng"):
        self.lang = lang
        self.enabled = False
        
        # Check if tesseract is available
        try:
            import pytesseract
            # Check availability (simple check)
            # This might fail if binary not in path
            # self.version = pytesseract.get_tesseract_version()
            self.enabled = True
        except Exception:
            print("[OCR] Tesseract not found or pytesseract library missing. OCR disabled.")

    def process_image(self, image_bytes: bytes) -> str:
        """
        Extract text from image bytes.
        """
        if not self.enabled:
            return ""

        try:
            from PIL import Image
            import pytesseract
            import io
            
            image = Image.open(io.BytesIO(image_bytes))
            
            # Simple preprocessing?
            # Tesseract usually handles standard images ok.
            
            text = pytesseract.image_to_string(image, lang=self.lang)
            return text.strip()
            
        except Exception as e:
            print(f"[OCR] Error processing image: {e}")
            return ""

    def process_file(self, file_path: str) -> str:
        if not self.enabled: return ""
        try:
             with open(file_path, "rb") as f:
                 return self.process_image(f.read())
        except Exception as e:
            print(f"[OCR] Error reading file {file_path}: {e}")
            return ""
