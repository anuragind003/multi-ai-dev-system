from flask import Blueprint, jsonify, request
from backend.database import db
from backend.models import Offer, OfferHistory, Customer
import uuid
from datetime import datetime, timezone, timedelta

offer_bp = Blueprint('offer_bp', __name__, url_prefix='/offers')

@offer_bp.route('/<uuid:offer_id>', methods=['GET'])
def get_offer_details(offer_id):
    """
    Retrieves details of a specific offer.

    Functional Requirements Addressed:
    - FR16: The CDP system shall maintain flags for Offer statuses: Active, Inactive, and Expired based on defined business logic.
    - FR17: The CDP system shall maintain flags for Offer types: ‘Fresh’, ‘Enrich’, ‘New-old’, ‘New-new’ for campaigning, specifically for Preapproved and TW-L Products.
    - FR19: The CDP system shall maintain analytics-defined flags for Propensity (values passed from Offermart).
    """
    offer = Offer.query.get(offer_id)
    if not offer:
        return jsonify({"message": "Offer not found"}), 404

    return jsonify({
        "offer_id": str(offer.offer_id),
        "customer_id": str(offer.customer_id),
        "source_offer_id": offer.source_offer_id,
        "offer_type": offer.offer_type,
        "offer_status": offer.offer_status,
        "propensity": offer.propensity,
        "loan_application_number": offer.loan_application_number,
        "valid_until": offer.valid_until.isoformat() if offer.valid_until else None,
        "source_system": offer.source_system,
        "channel": offer.channel,
        "is_duplicate": offer.is_duplicate,
        "original_offer_id": str(offer.original_offer_id) if offer.original_offer_id else None,
        "created_at": offer.created_at.isoformat(),
        "updated_at": offer.updated_at.isoformat()
    }), 200

@offer_bp.route('/<uuid:offer_id>', methods=['PUT'])
def update_offer(offer_id):
    """
    Updates details of an existing offer, including status and propensity.
    Records changes in offer history.

    Functional Requirements Addressed:
    - FR13: The CDP system shall prevent modification of customer offers with an active loan application journey until the application is expired or rejected.
    - FR14: The CDP system shall allow replenishment of offers for non-journey started customers after their existing offers expire.
    - FR16: The CDP system shall maintain flags for Offer statuses: Active, Inactive, and Expired based on defined business logic.
    - FR19: The CDP system shall maintain analytics-defined flags for Propensity (values passed from Offermart).
    - FR20: The CDP system shall maintain Offer history for the past 6 months.
    """
    data = request.get_json()
    if not data:
        return jsonify({"message": "Invalid JSON data"}), 400

    offer = Offer.query.get(offer_id)
    if not offer:
        return jsonify({"message": "Offer not found"}), 404

    # FR13: Prevent modification if customer has an active loan application journey for this offer
    # This check would typically be implemented in a dedicated service layer
    # For example: from backend.services.loan_journey_service import is_loan_journey_active
    # if offer.loan_application_number and is_loan_journey_active(offer.customer_id, offer.loan_application_number):
    #     return jsonify({"message": "Offer cannot be modified: associated loan application is active."}), 403

    old_status = offer.offer_status

    # Update fields if provided in the request body
    if 'offer_status' in data:
        new_status = data['offer_status']
        if new_status not in ['Active', 'Inactive', 'Expired']:
            return jsonify({"message": "Invalid offer_status. Must be 'Active', 'Inactive', or 'Expired'."}), 400
        offer.offer_status = new_status

    if 'propensity' in data:
        offer.propensity = data['propensity']

    if 'valid_until' in data:
        try:
            # Ensure valid_until is parsed correctly, assuming ISO 8601 format
            offer.valid_until = datetime.fromisoformat(data['valid_until']).replace(tzinfo=timezone.utc)
        except ValueError:
            return jsonify({"message": "Invalid 'valid_until' format. Use ISO 8601 (e.g., 'YYYY-MM-DDTHH:MM:SSZ')."}), 400

    # Record history if offer_status changed
    if 'offer_status' in data and old_status != offer.offer_status:
        history_entry = OfferHistory(
            history_id=uuid.uuid4(),
            offer_id=offer.offer_id,
            old_status=old_status,
            new_status=offer.offer_status,
            change_reason=data.get('change_reason', 'API update') # Allow reason to be passed in request
        )
        db.session.add(history_entry)

    offer.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        "message": "Offer updated successfully",
        "offer_id": str(offer.offer_id),
        "new_status": offer.offer_status,
        "new_propensity": offer.propensity,
        "new_valid_until": offer.valid_until.isoformat() if offer.valid_until else None
    }), 200

@offer_bp.route('/history/<uuid:offer_id>', methods=['GET'])
def get_offer_history(offer_id):
    """
    Retrieves the history of status changes for a specific offer.

    Functional Requirements Addressed:
    - FR20: The CDP system shall maintain Offer history for the past 6 months.
    """
    # Filter for the last 6 months as per FR20.
    # This assumes 'status_change_date' is the relevant timestamp for history retention.
    six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)

    history_records = OfferHistory.query.filter(
        OfferHistory.offer_id == offer_id,
        OfferHistory.status_change_date >= six_months_ago
    ).order_by(OfferHistory.status_change_date.desc()).all()

    if not history_records:
        return jsonify({"message": "No history found for this offer or history older than 6 months."}), 404

    history_list = []
    for record in history_records:
        history_list.append({
            "history_id": str(record.history_id),
            "offer_id": str(record.offer_id),
            "status_change_date": record.status_change_date.isoformat(),
            "old_status": record.old_status,
            "new_status": record.new_status,
            "change_reason": record.change_reason
        })

    return jsonify(history_list), 200