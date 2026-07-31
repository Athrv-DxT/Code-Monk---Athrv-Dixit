import httpx
import json
import sys

def test_hindi_discharge():
    print("======================================================================")
    print("RUNNING ADAPTATION TEST FOR HINDI RURAL PATIENT")
    print("======================================================================")
    
    url = "http://localhost:8000/api/v1/adapt"
    
    # Discharge instructions provided by the user
    source_content = """CITY GENERAL HOSPITAL
Discharge Instructions – Outpatient Procedure

Patient Name: John Doe
Date of Procedure: 28 July 2026
Procedure: Minor soft-tissue excision (left forearm)

You may leave the hospital today. Keep the dressing clean and dry for 48 hours. Do not soak the area in water. After 48 hours you may shower, but pat the area dry — do not rub.

Take paracetamol 500 mg every 6–8 hours if needed for pain. Do not exceed 4 grams in 24 hours. If pain is not controlled, contact the clinic.

Watch for: increasing redness, swelling, pus, fever above 38°C, or red streaks from the wound. If any of these occur, seek medical attention the same day.

Follow-up appointment is required in 7–10 days. The clinic will contact you to confirm the exact date and time. Bring this form and your insurance card.

If you have questions, call the Surgical Day Unit on 011-XXXX-XXXX between 9:00 and 17:00, Monday to Friday.

Note: Specific antibiotic instructions were discussed verbally with the patient. Written details are not included on this form."""

    # Payload targeting a rural patient in Hindi with low cognitive load constraints
    payload = {
        "content": source_content,
        "audience_profile": {
            "role": "patient",
            "domain_familiarity": "novice",
            "cognitive_access_needs": "low_cognitive_load",
            "preferred_language": "hi",
            "modality": "text"
        },
        "options": {
            "generate_multiple_profiles": False,
            "include_fidelity_note": True,
            "enable_external_lookup": False,
            "tts_output": True
        }
    }
    
    try:
        print("Sending request to local backend...")
        # High timeout because it makes real LLM API calls for extraction, adaptation, and verification
        res = httpx.post(url, json=payload, timeout=180.0)
        
        if res.status_code != 200:
            print(f"[-] Request failed with status code {res.status_code}")
            print(res.text)
            sys.exit(1)
            
        data = res.json()
        print("[+] Request completed successfully!")
        
        # Save response directly to a UTF-8 file to avoid Windows terminal chardet issues
        with open("tests/hindi_response.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("[+] Saved response to tests/hindi_response.json successfully.")
        
    except Exception as e:
        print(f"[-] Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_hindi_discharge()
