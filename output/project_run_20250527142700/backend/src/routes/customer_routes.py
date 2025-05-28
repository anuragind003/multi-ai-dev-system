from flask import Blueprint, jsonify, request
from backend.src.models import db, Customer, Offer
import uuid
from datetime import datetime

customers_bp = Blueprint('customers_bp', __name__, url_prefix='/customers')

@customers_bp.route('/<uuid:customer_id>', methods=['GET'])
def get_customer_profile(customer_id):
    """
    Retrieves a single customer's de-duplicated profile and associated active offers.

    Functional Requirements Addressed:
    - FR1: The CDP system shall perform customer deduplication to create a single profile view for Consumer Loan Products.
    - FR15: The CDP system shall maintain different customer attributes and customer segments.
    - FR16: The CDP system shall maintain flags for Offer statuses: Active, Inactive, and Expired based on defined business logic.
    """
    try:
        customer = Customer.query.get(customer_id)

        if not customer:
            return jsonify({"message": "Customer not found"}), 404

        # Retrieve active offers for the customer
        # FR16: Offer statuses: Active, Inactive, and Expired. We need 'Active' offers for the profile view.
        active_offers = Offer.query.filter_by(customer_id=customer.customer_id, offer_status='Active').all()

        offers_data = []
        for offer in active_offers:
            offers_data.append({
                "offer_id": str(offer.offer_id),
                "offer_type": offer.offer_type,
                "offer_status": offer.offer_status,
                "valid_until": offer.valid_until.isoformat() if offer.valid_until else None
            })

        customer_profile = {
            "customer_id": str(customer.customer_id),
            "mobile_number": customer.mobile_number,
            "pan_number": customer.pan_number,
            "aadhaar_number": customer.aadhaar_number,
            "ucid_number": customer.ucid_number,
            "customer_360_id": customer.customer_360_id,
            "is_dnd": customer.is_dnd,
            "segment": customer.segment,
            "attributes": customer.attributes,
            "offers": offers_data
        }

        return jsonify(customer_profile), 200

    except ValueError:
        # Handles cases where customer_id is not a valid UUID format
        return jsonify({"message": "Invalid customer ID format. Must be a valid UUID."}), 400
    except Exception as e:
        # Catch any other unexpected errors
        print(f"Error retrieving customer profile: {e}") # Log the error for debugging
        return jsonify({"message": "An internal server error occurred", "error": str(e)}), 500