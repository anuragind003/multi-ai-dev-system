import uuid
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app

# Define the Blueprint for offer-related routes
offer_bp = Blueprint('offers', __name__, url_prefix='/api/offers')


def get_db_connection():
    """
    Helper function to get a database connection.
    This function assumes that the database connection object (e.g., psycopg2
    connection) is stored in `current_app.db` after being initialized
    in the main Flask application setup (e.g., in app.py).
    """
    if not hasattr(current_app, 'db') or current_app.db is None:
        # In a real application, ensure your database connection
        # is properly initialized and accessible via current_app.db
        raise RuntimeError(
            "Database connection not initialized. "
            "Ensure `current_app.db` is set up."
        )
    return current_app.db


@offer_bp.route('/', methods=['POST'])
def create_offer():
    """
    Creates a new offer in the system.

    Expected request body:
    {
        "customer_id": "string (UUID)",
        "offer_type": "string",
        "offer_status": "string",
        "propensity": "string",
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD",
        "channel": "string"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    required_fields = [
        "customer_id", "offer_type", "offer_status", "propensity",
        "start_date", "end_date", "channel"
    ]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    offer_id = str(uuid.uuid4())
    customer_id = data['customer_id']
    offer_type = data['offer_type']
    offer_status = data['offer_status']
    propensity = data['propensity']
    channel = data['channel']

    try:
        start_date = datetime.strptime(
            data['start_date'], '%Y-%m-%d'
        ).date()
        end_date = datetime.strptime(
            data['end_date'], '%Y-%m-%d'
        ).date()
    except ValueError:
        return jsonify(
            {"error": "Invalid date format for start_date or end_date. "
                       "Use YYYY-MM-DD."}
        ), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO offers (
                offer_id, customer_id, offer_type, offer_status,
                propensity, start_date, end_date, channel
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                offer_id, customer_id, offer_type, offer_status,
                propensity, start_date, end_date, channel
            )
        )
        conn.commit()
        cursor.close()
        return jsonify({
            "status": "success",
            "message": "Offer created successfully",
            "offer_id": offer_id
        }), 201
    except Exception as e:
        if conn:
            conn.rollback()
        current_app.logger.error(f"Error creating offer: {e}")
        return jsonify(
            {"error": "Internal server error", "details": str(e)}
        ), 500
    finally:
        # In a production Flask app with a connection pool (e.g., psycopg2.pool)
        # or an ORM (e.g., SQLAlchemy), you would typically not close the
        # connection here, but rather return it to the pool or let the
        # ORM session manage it. For direct psycopg2, if not pooled,
        # conn.close() would be here. Assuming current_app.db is managed.
        pass


@offer_bp.route('/', methods=['GET'])
def get_all_offers():
    """
    Retrieves a list of all offers, with optional filtering capabilities.

    Query parameters:
        customer_id: Filter offers by a specific customer ID.
        status: Filter offers by their status (e.g., 'Active', 'Expired').
        type: Filter offers by their type (e.g., 'Fresh', 'Enrich').
    """
    customer_id = request.args.get('customer_id')
    status = request.args.get('status')
    offer_type = request.args.get('type')

    query = "SELECT * FROM offers WHERE 1=1"
    params = []

    if customer_id:
        query += " AND customer_id = %s"
        params.append(customer_id)
    if status:
        query += " AND offer_status = %s"
        params.append(status)
    if offer_type:
        query += " AND offer_type = %s"
        params.append(offer_type)

    # Add ordering for consistent results, e.g., by creation date
    query += " ORDER BY created_at DESC"

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        offers_data = cursor.fetchall()

        # Get column names from cursor description
        columns = [desc[0] for desc in cursor.description]
        offers_list = []
        for row in offers_data:
            offer_dict = dict(zip(columns, row))
            # Convert date/datetime objects to ISO format strings for JSON
            for key in ['start_date', 'end_date', 'created_at', 'updated_at']:
                if key in offer_dict and offer_dict[key] is not None:
                    offer_dict[key] = offer_dict[key].isoformat()
            offers_list.append(offer_dict)

        cursor.close()
        return jsonify(offers_list), 200
    except Exception as e:
        current_app.logger.error(f"Error retrieving offers: {e}")
        return jsonify(
            {"error": "Internal server error", "details": str(e)}
        ), 500
    finally:
        pass


@offer_bp.route('/<offer_id>', methods=['GET'])
def get_offer_by_id(offer_id):
    """
    Retrieves a single offer by its unique ID.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM offers WHERE offer_id = %s", (offer_id,))
        offer_data = cursor.fetchone()
        cursor.close()

        if not offer_data:
            return jsonify({"error": "Offer not found"}), 404

        # Get column names from cursor description
        columns = [desc[0] for desc in cursor.description]
        offer_dict = dict(zip(columns, offer_data))

        # Convert date/datetime objects to ISO format strings for JSON
        for key in ['start_date', 'end_date', 'created_at', 'updated_at']:
            if key in offer_dict and offer_dict[key] is not None:
                offer_dict[key] = offer_dict[key].isoformat()

        return jsonify(offer_dict), 200
    except Exception as e:
        current_app.logger.error(f"Error retrieving offer {offer_id}: {e}")
        return jsonify(
            {"error": "Internal server error", "details": str(e)}
        ), 500
    finally:
        pass


@offer_bp.route('/<offer_id>', methods=['PUT'])
def update_offer(offer_id):
    """
    Updates an existing offer's details based on the provided offer ID.
    Allows partial updates.

    Expected request body (at least one field required):
    {
        "offer_type": "string",
        "offer_status": "string",
        "propensity": "string",
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD",
        "channel": "string"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    set_clauses = []
    params = []

    # Dynamically build the SET clause for the UPDATE query
    if 'offer_type' in data:
        set_clauses.append("offer_type = %s")
        params.append(data['offer_type'])
    if 'offer_status' in data:
        set_clauses.append("offer_status = %s")
        params.append(data['offer_status'])
    if 'propensity' in data:
        set_clauses.append("propensity = %s")
        params.append(data['propensity'])
    if 'start_date' in data:
        try:
            start_date = datetime.strptime(
                data['start_date'], '%Y-%m-%d'
            ).date()
            set_clauses.append("start_date = %s")
            params.append(start_date)
        except ValueError:
            return jsonify(
                {"error": "Invalid start_date format. Use YYYY-MM-DD."}
            ), 400
    if 'end_date' in data:
        try:
            end_date = datetime.strptime(
                data['end_date'], '%Y-%m-%d'
            ).date()
            set_clauses.append("end_date = %s")
            params.append(end_date)
        except ValueError:
            return jsonify(
                {"error": "Invalid end_date format. Use YYYY-MM-DD."}
            ), 400
    if 'channel' in data:
        set_clauses.append("channel = %s")
        params.append(data['channel'])

    if not set_clauses:
        return jsonify({"error": "No fields provided for update"}), 400

    # Always update the 'updated_at' timestamp
    set_clauses.append("updated_at = CURRENT_TIMESTAMP")

    query = f"UPDATE offers SET {', '.join(set_clauses)} WHERE offer_id = %s"
    params.append(offer_id)  # Add offer_id for the WHERE clause

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        rows_affected = cursor.rowcount
        cursor.close()

        if rows_affected == 0:
            return jsonify(
                {"error": "Offer not found or no changes were made"}
            ), 404

        return jsonify({
            "status": "success",
            "message": "Offer updated successfully",
            "offer_id": offer_id
        }), 200
    except Exception as e:
        if conn:
            conn.rollback()
        current_app.logger.error(f"Error updating offer {offer_id}: {e}")
        return jsonify(
            {"error": "Internal server error", "details": str(e)}
        ), 500
    finally:
        pass