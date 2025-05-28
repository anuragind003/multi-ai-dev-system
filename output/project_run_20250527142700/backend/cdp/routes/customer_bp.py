from flask import Blueprint, jsonify, request
from backend.cdp.models import db, Customer, Offer
import uuid

customer_bp = Blueprint('customer_bp', __name__, url_prefix='/customers')

@customer_bp.route('/<uuid:customer_id>', methods=['GET'])
def get_customer_profile(customer_id):
    """
    Retrieves a single customer's de-duplicated profile and associated active offers.

    Functional Requirements Addressed:
    - FR1: The CDP system shall perform customer deduplication to create a single profile view for Consumer Loan Products.
    - FR15: The CDP system shall maintain different customer attributes and customer segments.
    - FR16: The CDP system shall maintain flags for Offer statuses: Active, Inactive, and Expired based on defined business logic.

    API Endpoint: /customers/:customer_id (GET)
    """
    customer = Customer.query.get(customer_id)

    if not customer:
        return jsonify({"message": "Customer not found"}), 404

    # Retrieve active offers for the customer
    # FR16: Maintain flags for Offer statuses: Active, Inactive, and Expired
    active_offers = Offer.query.filter_by(
        customer_id=customer.customer_id,
        offer_status='Active'
    ).all()

    offers_data = []
    for offer in active_offers:
        offers_data.append({
            "offer_id": str(offer.offer_id),
            "offer_type": offer.offer_type,
            "offer_status": offer.offer_status,
            "valid_until": offer.valid_until.isoformat() if offer.valid_until else None,
            "propensity": offer.propensity,
            "loan_application_number": offer.loan_application_number,
            "source_system": offer.source_system,
            "channel": offer.channel,
            "is_duplicate": offer.is_duplicate,
            "original_offer_id": str(offer.original_offer_id) if offer.original_offer_id else None,
            "created_at": offer.created_at.isoformat() if offer.created_at else None,
            "updated_at": offer.updated_at.isoformat() if offer.updated_at else None
        })

    # FR15: Maintain different customer attributes and customer segments.
    # The `attributes` field is JSONB, so it can hold various attributes.
    customer_data = {
        "customer_id": str(customer.customer_id),
        "mobile_number": customer.mobile_number,
        "pan_number": customer.pan_number,
        "aadhaar_number": customer.aadhaar_number,
        "ucid_number": customer.ucid_number,
        "customer_360_id": customer.customer_360_id,
        "is_dnd": customer.is_dnd,
        "segment": customer.segment,
        "attributes": customer.attributes, # This is JSONB, will be dict in Python
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
        "updated_at": customer.updated_at.isoformat() if customer.updated_at else None,
        "offers": offers_data
    }

    return jsonify(customer_data), 200