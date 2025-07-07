import requests
import json

def test_enhanced_recovery_integration():
    """Test that enhanced recovery system is properly integrated"""
    
    base_url = "http://localhost:8001"
    
    # Test 1: Check recovery stats endpoint
    try:
        response = requests.get(f"{base_url}/api/recovery/stats")
        if response.status_code == 200:
            stats = response.json()
            print("✅ Recovery stats endpoint working:")
            print(json.dumps(stats, indent=2))
        else:
            print(f"❌ Recovery stats failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Recovery stats error: {e}")
    
    # Test 2: Create enhanced workflow session
    try:
        create_response = requests.post(f"{base_url}/api/workflow/create", 
            json={"brd_content": "Test BRD for enhanced recovery"})
        
        if create_response.status_code == 200:
            session_data = create_response.json()
            session_id = session_data["session_id"]
            print(f"✅ Enhanced workflow session created: {session_id}")
            
            # Test 3: Check session recovery info
            recovery_response = requests.get(f"{base_url}/api/recovery/sessions/{session_id}/recovery-info")
            if recovery_response.status_code == 200:
                recovery_info = recovery_response.json()
                print("✅ Session recovery info available:")
                print(json.dumps(recovery_info, indent=2))
            else:
                print(f"❌ Recovery info failed: {recovery_response.status_code}")
                
        else:
            print(f"❌ Session creation failed: {create_response.status_code}")
            
    except Exception as e:
        print(f"❌ Session test error: {e}")

if __name__ == "__main__":
    print("🧪 Testing Enhanced Recovery Integration")
    print("=" * 50)
    test_enhanced_recovery_integration()