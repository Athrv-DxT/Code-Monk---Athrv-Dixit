import unittest
from app.privacy.validators import verify_verhoeff, verify_luhn, verify_pan_syntax
from app.privacy.vault import PIIVault
from app.privacy.detector import PIIDetector
from app.privacy.masker import PIIMasker
from app.privacy.reinserter import PIIReinserter
from app.privacy.logger import PIILogger
from app.privacy import mask_document, reinsert_document, get_pii_summary

class TestPrivacyValidators(unittest.TestCase):
    def test_verhoeff(self):
        # Valid Aadhaar numbers must pass Verhoeff
        self.assertTrue(verify_verhoeff("366802753381"))
        self.assertTrue(verify_verhoeff("5489 8402 1821"))
        self.assertFalse(verify_verhoeff("366802753382")) # Invalid check digit
        self.assertFalse(verify_verhoeff("123456789012")) # Invalid check digit

    def test_luhn(self):
        # Valid credit cards (length >= 13)
        self.assertTrue(verify_luhn("4992739871630013"))
        self.assertFalse(verify_luhn("4992739871630014"))

    def test_pan_syntax(self):
        self.assertTrue(verify_pan_syntax("ABCPD1234F")) # Valid Personal status syntax
        self.assertTrue(verify_pan_syntax("APGPD7711M")) # Valid Personal status syntax
        self.assertFalse(verify_pan_syntax("ABCDE12345")) # Missing trailing letter
        self.assertFalse(verify_pan_syntax("ABCD1234F")) # Too few letters

class TestPIIVault(unittest.TestCase):
    def test_vault_storage(self):
        vault = PIIVault()
        token1 = vault.store("PERSON", "Rahul Sharma")
        token2 = vault.store("PERSON", "John Doe")
        token3 = vault.store("PERSON", "Rahul Sharma") # Identical value
        
        self.assertEqual(token1, "[PERSON_001]")
        self.assertEqual(token2, "[PERSON_002]")
        self.assertEqual(token3, "[PERSON_001]") # Reused
        
        self.assertEqual(vault.get("[PERSON_001]"), "Rahul Sharma")
        self.assertTrue(vault.contains("[PERSON_002]"))
        
        vault.clear()
        self.assertFalse(vault.contains("[PERSON_001]"))

class TestPIIDetectorAndMasker(unittest.TestCase):
    def test_detection_and_masking(self):
        text = "Hello, I am Rahul Sharma and my Aadhaar number is 3668 0275 3381. You can call me at 9876543210 or email rahul@gmail.com."
        
        # Test convenience wrapper
        masked, detections, vault = mask_document(text)
        
        # Verify Aadhaar is detected
        aadhaar_detected = any(d.entity_type == "AADHAAR" for d in detections)
        self.assertTrue(aadhaar_detected)
        
        # Verify Person name is detected
        person_detected = any(d.entity_type == "PERSON" for d in detections)
        self.assertTrue(person_detected)
        
        # Verify masked text does not contain original values
        self.assertNotIn("Rahul Sharma", masked)
        self.assertNotIn("3668 0275 3381", masked)
        self.assertNotIn("9876543210", masked)
        self.assertNotIn("rahul@gmail.com", masked)
        
        # Verify tokens are inserted
        self.assertIn("[PERSON_001]", masked)
        self.assertIn("[AADHAAR_001]", masked)
        
        # Verify summary count is correct
        summary = get_pii_summary(detections)
        self.assertIn("1 Aadhaar", summary)
        self.assertIn("1 Person", summary)
        
        # Test reinsertion
        unmasked = reinsert_document(masked, vault)
        self.assertEqual(unmasked, text)
        
        vault.clear()

    def test_property_legal_detection(self):
        text = "Registry No. 1234/2026 for Plot No 45-B under Survey Number 809/206."
        detector = PIIDetector()
        detections = detector.detect(text)
        
        self.assertTrue(len(detections) >= 2)
        entity_types = [d.entity_type for d in detections]
        self.assertIn("PROPERTY_ID", entity_types)
        self.assertIn("LEGAL_DOCUMENT_ID", entity_types)
