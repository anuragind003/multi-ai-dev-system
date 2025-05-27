import httpx
from typing import Optional, Dict, Any
import os

# In a real application, these would be loaded from environment variables or a dedicated config service.
# For demonstration purposes, we'll use placeholders and attempt to load from environment variables.
CUSTOMER_360_API_BASE_URL = os.getenv("CUSTOMER_360_API_BASE_URL", "http://customer360-api.example.com/api/v1")
CUSTOMER_360_API_KEY = os.getenv("CUSTOMER_360_API_KEY", "your_customer_360_api_key_here")


class Customer360Integration:
    """
    Handles integration with the external Customer 360 system for deduplication and
    retrieval of live book customer data.
    """

    def __init__(self, base_url: str = CUSTOMER_360_API_BASE_URL, api_key: str = CUSTOMER_360_API_KEY):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        # Using AsyncClient for FastAPI's async nature
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=self.headers)

    async def check_customer_exists(
        self,
        mobile_number: Optional[str] = None,
        pan_number: Optional[str] = None,
        aadhaar_ref_number: Optional[str] = None,
        ucid_number: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Checks if a customer exists in the Customer 360 live book based on provided identifiers.
        This is crucial for FR5: "deduplication against the live book (from Customer 360)".

        Args:
            mobile_number: Customer's mobile number.
            pan_number: Customer's PAN number.
            aadhaar_ref_number: Customer's Aadhaar reference number.
            ucid_number: Customer's UCID number.

        Returns:
            A dictionary containing customer data from Customer 360 if found,
            otherwise None. The dictionary structure will depend on the Customer 360 API.
            Expected keys might include 'customer_id', 'mobile_number', 'pan_number', etc.
        """
        search_params = {}
        if mobile_number:
            search_params["mobile_number"] = mobile_number
        if pan_number:
            search_params["pan_number"] = pan_number
        if aadhaar_ref_number:
            search_params["aadhaar_ref_number"] = aadhaar_ref_number
        if ucid_number:
            search_params["ucid_number"] = ucid_number

        if not search_params:
            # Log or raise an error if no search criteria are provided
            print("Warning: No search criteria provided for Customer 360 lookup.")
            return None

        try:
            # Simulate an API call to Customer 360's customer lookup endpoint.
            # The actual endpoint path and query parameters would be defined by the C360 API spec.
            # We assume a GET request to a '/customers/lookup' endpoint that accepts identifiers as query params.
            response = await self.client.get("/customers/lookup", params=search_params, timeout=10.0)
            response.raise_for_status()  # Raise an exception for 4xx/5xx responses

            customer_data = response.json()

            # Assuming Customer 360 returns a single customer object if found, or an empty response/list if not.
            # Adjust this logic based on the actual Customer 360 API response format.
            if customer_data and isinstance(customer_data, dict) and customer_data.get("customer_id"):
                return customer_data
            elif isinstance(customer_data, list) and customer_data:
                # If the API returns a list of potential matches, we might take the first one
                # or apply further logic to determine the best match. For simplicity, taking first.
                return customer_data[0]
            else:
                return None

        except httpx.RequestError as exc:
            # Log the error for monitoring and debugging
            print(f"Customer360Integration: An error occurred while requesting Customer 360: {exc}")
            # Depending on business requirements, you might want to re-raise,
            # return a specific error code, or fall back to local deduplication.
            return None
        except httpx.HTTPStatusError as exc:
            # Log HTTP errors (e.g., 404 Not Found, 500 Internal Server Error from C360)
            print(f"Customer360Integration: Error response {exc.response.status_code} from Customer 360: {exc.response.text}")
            return None
        except Exception as e:
            # Catch any other unexpected errors during the process
            print(f"Customer360Integration: An unexpected error occurred during C360 lookup: {e}")
            return None

    async def get_customer_details(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves full customer details from Customer 360 by a known customer_id.
        This might be used if `check_customer_exists` returns only a minimal ID,
        and more comprehensive data is needed.

        Args:
            customer_id: The unique identifier of the customer in Customer 360.

        Returns:
            A dictionary containing the full customer data, or None if not found or an error occurs.
        """
        try:
            response = await self.client.get(f"/customers/{customer_id}", timeout=10.0)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            print(f"Customer360Integration: An error occurred fetching details for C360 ID {customer_id}: {exc}")
            return None
        except httpx.HTTPStatusError as exc:
            print(f"Customer360Integration: Error response {exc.response.status_code} fetching details for C360 ID {customer_id}: {exc.response.text}")
            return None
        except Exception as e:
            print(f"Customer360Integration: An unexpected error occurred fetching C360 details: {e}")
            return None

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Ensures the httpx client is closed properly when used as an async context manager."""
        await self.client.aclose()

    async def __aenter__(self):
        """Allows the httpx client to be used as an async context manager."""
        return self