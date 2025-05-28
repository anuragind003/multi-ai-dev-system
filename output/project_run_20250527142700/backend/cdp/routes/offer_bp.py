from flask import Blueprint, jsonify, request
from backend.models import db, Offer, OfferHistory, Customer
import uuid
from datetime import datetime

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
def update_offer_details(offer_id):
    """
    Updates details of a specific offer, including status.
    This endpoint can be used by internal processes (e.g., LOS integration, scheduled jobs)
    to update offer status based on business logic.

    Functional Requirements Addressed:
    - FR7: The CDP system shall update old offers in Analytics Offermart with new real-time data from CDP for the same customer.
    - FR16: The CDP system shall maintain flags for Offer statuses: Active, Inactive, and Expired based on defined business logic.
    - FR36: The CDP system shall mark offers as expired if the loan application number (LAN) validity is over for journey-started customers.
    """
    offer = Offer.query.get(offer_id)
    if not offer:
        return jsonify({"message": "Offer not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"message": "Invalid JSON data"}), 400

    old_status = offer.offer_status
    new_status = data.get('offer_status')
    change_reason = data.get('change_reason', 'API Update')

    # FR13: Prevent modification of customer offers with an active loan application journey
    # This logic would require checking the 'events' table or an external LOS status.
    # For now, it's a placeholder.
    # if offer.loan_application_number and offer.offer_status == 'Active' and new_status != 'Expired':
    #     # Check LOS events for active journey status
    #     # If active journey, return error
    #     # return jsonify({"message": "Cannot modify offer with active loan application journey"}), 403
    pass

    if new_status and new_status != old_status:
        offer.offer_status = new_status
        # Record status change in offer_history
        history_entry = OfferHistory(
            offer_id=offer.offer_id,
            old_status=old_status,
            new_status=new_status,
            change_reason=change_reason
        )
        db.session.add(history_entry)

    # Update other fields if provided
    offer.propensity = data.get('propensity', offer.propensity)
    offer.loan_application_number = data.get('loan_application_number', offer.loan_application_number)
    
    valid_until_str = data.get('valid_until')
    if valid_until_str:
        try:
            offer.valid_until = datetime.fromisoformat(valid_until_str)
        except ValueError:
            return jsonify({"message": "Invalid 'valid_until' date format. Use ISO 8601."}), 400

    offer.is_duplicate = data.get('is_duplicate', offer.is_duplicate)
    offer.original_offer_id = data.get('original_offer_id', offer.original_offer_id)

    offer.updated_at = datetime.now()

    try:
        db.session.commit()
        return jsonify({
            "message": "Offer updated successfully",
            "offer_id": str(offer.offer_id),
            "new_status": offer.offer_status
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error updating offer: {str(e)}"}), 500

@offer_bp.route('/<uuid:offer_id>/history', methods=['GET'])
def get_offer_history(offer_id):
    """
    Retrieves the history of status changes for a specific offer.

    Functional Requirements Addressed:
    - FR20: The CDP system shall maintain Offer history for the past 6 months.
    - NFR10: Offer history shall be maintained for 6 months.
    """
    # Filter for history within the last 6 months as per FR20/NFR10
    six_months_ago = datetime.now() - timedelta(days=180)

    history = OfferHistory.query.filter(
        OfferHistory.offer_id == offer_id,
        OfferHistory.status_change_date >= six_months_ago
    ).order_by(OfferHistory.status_change_date.desc()).all()

    if not history:
        return jsonify({"message": "No history found for this offer within the last 6 months"}), 404

    history_data = []
    for entry in history:
        history_data.append({
            "history_id": str(entry.history_id),
            "offer_id": str(entry.offer_id),
            "status_change_date": entry.status_change_date.isoformat(),
            "old_status": entry.old_status,
            "new_status": entry.new_status,
            "change_reason": entry.change_reason
        })

    return jsonify(history_data), 200

# Helper for timedelta, needs to be imported
from datetime import timedelta