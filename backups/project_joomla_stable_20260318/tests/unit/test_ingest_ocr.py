
import unittest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.getcwd())
try:
    from src.ingest.process_one import extract_text_with_tables
    from src.ingest.ocr_processor import OCRProcessor
except ImportError:
    pass

class TestOCRIntegration(unittest.TestCase):
    def test_ocr_extraction(self):
        print("\n--- Test: OCR Integration in HTML Processing ---")
        
        html = """
        <html><body>
        <h1>Test Page</h1>
        <img src="test.png" alt="Test Image">
        <p>Content</p>
        </body></html>
        """
        
        # Mock requests.get and OCRProcessor.process_image
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.ok = True
            mock_response.content = b'fake_image_data'
            mock_get.return_value = mock_response
            
            # Patch the class where it is defined, because process_one imports it
            with patch('src.ingest.ocr_processor.OCRProcessor') as MockOCR:
                mock_ocr_instance = MockOCR.return_value
                mock_ocr_instance.enabled = True
                mock_ocr_instance.process_image.return_value = "Extracted Text 123"
                
                text, links, images = extract_text_with_tables(html, base_url="http://test.com")
                
                print(f"Extracted Text:\n{text}")
                
                self.assertIn("Extracted Text 123", text)
                self.assertIn("[Image Content (Test Image): Extracted Text 123]", text)
                print("OCR Text successfully appended to content.")

if __name__ == "__main__":
    unittest.main()
