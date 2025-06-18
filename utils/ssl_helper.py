"""
SSL Certificate Handler for Multi-AI Development System.
Provides utilities to fix common SSL certificate issues with external services.
"""

import os
import ssl
import certifi
import urllib3
import requests
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

class SSLHelper:
    """Helper class for handling SSL certificate issues."""
    
    @staticmethod
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
        
        # Set proper security options and SNI handling
        if hostname:
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
        
        # Disable vulnerable protocols
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        
        return context

    @staticmethod
    def patch_ssl_for_langsmith():
        """
        Apply SSL patches specifically for LangSmith connections.
        
        Returns:
            bool: True if patching was successful
        """
        try:
            # Set environment variables for certificate handling
            os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
            os.environ['SSL_CERT_FILE'] = certifi.where()
            
            # Fix for LangSmith endpoint
            if os.environ.get("LANGCHAIN_ENDPOINT", "").endswith("langchain.cloud"):
                # Use smith.langchain.com endpoint instead which has better SSL setup
                os.environ["LANGCHAIN_ENDPOINT"] = "https://smith.langchain.com"
                logger.info("Changed LANGCHAIN_ENDPOINT to smith.langchain.com")
            
            # Patch urllib3 to use modern ciphers
            urllib3.util.ssl_.DEFAULT_CIPHERS = 'HIGH:!DH:!aNULL'
            
            # Patch requests session to use our custom SSL context for LangSmith
            old_merge_env = requests.Session.merge_environment_settings
            
            def new_merge_env(self, url, proxies, stream, verify, cert):
                settings = old_merge_env(self, url, proxies, stream, verify, cert)
                
                # Use custom context for LangSmith domains
                parsed_url = urlparse(url)
                hostname = parsed_url.hostname
                if hostname and ('langchain' in hostname):
                    settings['verify'] = certifi.where()
                    settings['ssl_context'] = SSLHelper.setup_ssl_context(hostname)
                    
                return settings
                
            requests.Session.merge_environment_settings = new_merge_env
            return True
            
        except Exception as e:
            logger.error(f"SSL patching failed: {e}")
            return False
    
    @staticmethod
    def test_langsmith_connection():
        """Test connection to LangSmith API with enhanced SSL handling."""
        try:
            # Apply SSL patching
            SSLHelper.patch_ssl_for_langsmith()
            
            # Add custom headers for reliable connection
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Multi-AI-Dev-System/1.0"
            }
            
            # Try alternate endpoints
            endpoints = [
                "https://smith.langchain.com/info", 
                "https://api.smith.langchain.com/info"
            ]
            
            for endpoint in endpoints:
                try:
                    response = requests.get(endpoint, headers=headers, timeout=5)
                    if response.status_code == 200:
                        logger.info(f"LangSmith connection successful to {endpoint}")
                        return True, f"Connection successful to {endpoint}"
                except Exception as e:
                    logger.warning(f"Failed to connect to {endpoint}: {e}")
                    continue
                    
            return False, "Failed to connect to any LangSmith endpoint"
            
        except Exception as e:
            return False, f"Connection test failed: {e}"