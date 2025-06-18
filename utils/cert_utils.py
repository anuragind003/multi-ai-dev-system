import os
import certifi
import ssl
import requests
import urllib3
from urllib.parse import urlparse

def setup_ssl_context(hostname=None):
    """
    Configure SSL context with improved certificate handling.
    
    Args:
        hostname: Optional target hostname for SNI handling
    
    Returns:
        An SSLContext object configured for secure connections
    """
    # Create a custom SSL context using the certifi bundle
    context = ssl.create_default_context(cafile=certifi.where())
    
    # Configure to use environment-specified cert files if available
    custom_ca_bundle = os.getenv("SSL_CERT_FILE")
    if custom_ca_bundle and os.path.exists(custom_ca_bundle):
        context.load_verify_locations(cafile=custom_ca_bundle)
    
    # Ensure that SNI (Server Name Indication) is properly handled
    if hostname:
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
    
    # Set proper security options
    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3
    context.options |= ssl.OP_NO_TLSv1
    context.options |= ssl.OP_NO_TLSv1_1
    
    # Apply the SSL context to urllib3
    urllib3.util.ssl_.DEFAULT_CIPHERS = 'HIGH:!DH:!aNULL'
    
    return context

def apply_global_ssl_patch():
    """
    Apply global SSL patches to fix common certificate issues.
    """
    # Add custom CA certificates directory
    cert_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.certs')
    os.makedirs(cert_dir, exist_ok=True)
    
    # Set environment variables for certificate handling
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
    
    # Patch requests to use our custom SSL context
    old_merge_environment_settings = requests.Session.merge_environment_settings
    
    def new_merge_environment_settings(self, url, proxies, stream, verify, cert):
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        
        settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
        
        # Customize settings for LangSmith specifically
        if hostname and ('langchain.cloud' in hostname or 'smith.langchain.com' in hostname):
            settings['verify'] = certifi.where()
            # Use a custom context for LangSmith
            ssl_context = setup_ssl_context(hostname)
            settings['ssl_context'] = ssl_context
            
        return settings
        
    requests.Session.merge_environment_settings = new_merge_environment_settings

def test_langsmith_connection():
    """Test connection to LangSmith API with enhanced SSL handling."""
    try:
        # Apply SSL patching before testing
        apply_global_ssl_patch()
        
        # Add custom headers and settings for reliable connection
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Multi-AI-Dev-System/1.0"
        }
        
        # Test connection
        response = requests.get(
            "https://api.smith.langchain.com/info",
            headers=headers,
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