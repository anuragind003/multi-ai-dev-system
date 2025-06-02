import os
import certifi
import ssl
import requests
import urllib3

def setup_ssl_context():
    """Configure SSL context with improved certificate handling."""
    # Use certifi's certificate bundle
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
    os.environ['SSL_CERT_FILE'] = certifi.where()
    
    # Create a custom SSL context that works with LangSmith
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    
    # Configure urllib3 to use this context
    urllib3.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'
    
    return ssl_context

def test_langsmith_connection():
    """Test connection to LangSmith API."""
    try:
        # Setup SSL context
        setup_ssl_context()
        
        # Test connection
        response = requests.get(
            "https://api.smith.langchain.com/info",
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        return True, "Connection successful"
    except requests.exceptions.SSLError as e:
        return False, f"SSL Error: {str(e)}"
    except requests.exceptions.RequestException as e:
        return False, f"Request Error: {str(e)}"
    except Exception as e:
        return False, f"Unknown Error: {str(e)}"