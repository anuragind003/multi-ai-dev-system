from app.routes.lead_routes import lead_bp
from app.routes.admin import admin_bp
from app.routes.reports import reports_bp

# This __init__.py file serves to initialize the 'v1' API package.
# It imports and exposes the blueprints defined in the 'app.routes' module,
# making them accessible via 'app.api.v1'.
#
# The API endpoints defined in the system design (e.g., /api/leads, /api/admin/upload)
# do not include a '/v1' prefix. Therefore, this package acts primarily as an
# organizational container for the current version of the API, and the individual
# blueprints (lead_bp, admin_bp, reports_bp) are responsible for their own
# URL prefixes (e.g., /api/leads, /api/admin, /api/reports).
#
# The main Flask application (app.py) will import these blueprints from
# 'app.api.v1' and register them directly.