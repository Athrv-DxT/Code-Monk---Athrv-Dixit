import sys
import os
import httpx

def run_smoke_test():
    # Retrieve BASE_URL from command line argument, environment variable, or use default
    base_url = "http://localhost:8000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    elif os.environ.get("BASE_URL"):
        base_url = os.environ.get("BASE_URL")
        
    print(f"======================================================================")
    print(f"RUNNING SMOKE TEST ON: {base_url}")
    print(f"======================================================================")
    
    client = httpx.Client(timeout=30.0)
    
    # 1. PING healthcheck
    health_url = f"{base_url}/api/v1/health"
    try:
        print(f"1. Checking backend health status at {health_url}...")
        res = client.get(health_url)
        if res.status_code != 200:
            print(f"[-] Healthcheck failed: {res.status_code} - {res.text}")
            sys.exit(1)
        data = res.json()
        print(f"[+] Healthcheck passed. Status: {data.get('status')}, Neo4j: {data.get('neo4j')}")
    except Exception as e:
        print(f"[-] Failed to connect to healthcheck endpoint: {e}")
        sys.exit(1)
        
    # 2. RUN adaptation pipeline
    adapt_url = f"{base_url}/api/v1/adapt"
    payload = {
        "content": "Tenant notice: Inspections begin on August 15, 2026. Submit key waivers 48 hours prior or face a $150 fine.",
        "audience_profile": {
            "role": "general_adult",
            "domain_familiarity": "intermediate",
            "cognitive_access_needs": "standard",
            "preferred_language": "en",
            "modality": "text"
        },
        "options": {
            "generate_multiple_profiles": False,
            "include_fidelity_note": True,
            "enable_external_lookup": False,
            "tts_output": False
        }
    }
    
    try:
        print(f"\n2. Triggering adaptation pipeline at {adapt_url}...")
        res = client.post(adapt_url, json=payload)
        if res.status_code != 200:
            print(f"[-] Pipeline run failed: {res.status_code} - {res.text}")
            sys.exit(1)
            
        result = res.json()
        
        # Verify response structure contract
        assert "run_id" in result, "Missing run_id in response"
        assert "domain" in result, "Missing domain in response"
        assert "versions" in result, "Missing versions list"
        assert len(result["versions"]) > 0, "Versions list is empty"
        
        version = result["versions"][0]
        assert "adapted_content" in version, "Missing adapted_content in version"
        assert "fidelity_note" in version, "Missing fidelity_note"
        
        print(f"[+] Pipeline run completed successfully.")
        print(f"    - Run ID: {result['run_id']}")
        print(f"    - Domain: {result['domain']}")
        print(f"    - Risk: {result['risk_level']}")
        print(f"    - Compliant Rewrite: \"{version['adapted_content'][:60]}...\"")
        print(f"    - Compliance check: {version['fidelity_note']}")
        print(f"======================================================================")
        print(f"[SUCCESS] All smoke test verification steps passed.")
        print(f"======================================================================")
        
    except Exception as e:
        print(f"[-] Error during pipeline verification: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_smoke_test()
