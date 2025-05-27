import uuid

def generate_uuid():
    """
    Generates a unique UUID string.
    Used for primary keys like customer_id, offer_id, event_id, etc.,
    as per system design notes.
    """
    return str(uuid.uuid4())