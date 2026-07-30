import unittest
import io
import os
from fastapi.testclient import TestClient
from app.main import app
from pypdf import PdfWriter

class TestPDFUpload(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_pdf_upload_parsing(self):
        # 1. Create a simple mock PDF in memory
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        
        # Save mock PDF to bytes
        pdf_bytes = io.BytesIO()
        writer.write(pdf_bytes)
        pdf_bytes.seek(0)
        
        # 2. Upload the mock PDF file using the TestClient
        response = self.client.post(
            "/api/v1/upload-file",
            files={"file": ("test_doc.pdf", pdf_bytes, "application/pdf")}
        )
        
        # 3. Assert response status and format
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn("text", result)
        # Blank page won't have text, but response must be valid JSON text container
        self.assertEqual(type(result["text"]), str)

        print("\n[+] PDF Upload & Parsing Test Passed successfully!")

if __name__ == "__main__":
    unittest.main()
