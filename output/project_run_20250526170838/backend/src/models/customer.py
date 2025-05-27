import uuid
from datetime import datetime
from backend.src.extensions import db # Assuming db is initialized as SQLAlchemy instance here

class Customer(db.Model):
    """
    Represents a customer in the CDP system.
    Corresponds to the 'customers' table in the database schema.
    """
    __tablename__ = 'customers'

    customer_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    mobile_number = db.Column(db.Text, unique=True, nullable=True)
    pan_number = db.Column(db.Text, unique=True, nullable=True)
    aadhaar_number = db.Column(db.Text, unique=True, nullable=True)
    ucid_number = db.Column(db.Text, unique=True, nullable=True)
    loan_application_number = db.Column(db.Text, unique=True, nullable=True)
    dnd_flag = db.Column(db.Boolean, default=False, nullable=False)
    segment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    # Assuming Offer and Event models are defined in their respective files
    # 'cascade="all, delete-orphan"' ensures that related offers and events are deleted if a customer is deleted.
    offers = db.relationship('Offer', backref='customer', lazy=True, cascade="all, delete-orphan")
    events = db.relationship('Event', backref='customer', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Customer {self.customer_id} | Mobile: {self.mobile_number or 'N/A'}>"

    def to_dict(self):
        """
        Converts the Customer object to a dictionary, useful for API responses.
        """
        return {
            'customer_id': self.customer_id,
            'mobile_number': self.mobile_number,
            'pan_number': self.pan_number,
            'aadhaar_number': self.aadhaar_number,
            'ucid_number': self.ucid_number,
            'loan_application_number': self.loan_application_number,
            'dnd_flag': self.dnd_flag,
            'segment': self.segment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def find_by_identifiers(mobile=None, pan=None, aadhaar=None, ucid=None, lan=None):
        """
        Finds a customer by any of the provided unique identifiers.
        This is crucial for deduplication logic (FR3, FR4, FR5, FR6).
        Returns the first customer found matching any identifier, or None.
        """
        filters = []
        if mobile:
            filters.append(Customer.mobile_number == mobile)
        if pan:
            filters.append(Customer.pan_number == pan)
        if aadhaar:
            filters.append(Customer.aadhaar_number == aadhaar)
        if ucid:
            filters.append(Customer.ucid_number == ucid)
        if lan:
            filters.append(Customer.loan_application_number == lan)
        
        if not filters:
            return None # No identifiers provided

        return Customer.query.filter(db.or_(*filters)).first()

    @staticmethod
    def create_customer(data):
        """
        Creates a new customer record in the database.
        Args:
            data (dict): A dictionary containing customer attributes.
        Returns:
            Customer: The newly created Customer object.
        """
        new_customer = Customer(
            mobile_number=data.get('mobile_number'),
            pan_number=data.get('pan_number'),
            aadhaar_number=data.get('aadhaar_number'),
            ucid_number=data.get('ucid_number'),
            loan_application_number=data.get('loan_application_number'),
            dnd_flag=data.get('dnd_flag', False),
            segment=data.get('segment')
        )
        db.session.add(new_customer)
        db.session.commit()
        return new_customer

    def update_customer(self, data):
        """
        Updates an existing customer record in the database.
        Args:
            data (dict): A dictionary containing customer attributes to update.
        Returns:
            Customer: The updated Customer object.
        """
        for key, value in data.items():
            # Prevent updating primary key or auto-generated timestamps directly
            if hasattr(self, key) and key not in ['customer_id', 'created_at', 'updated_at']:
                setattr(self, key, value)
        self.updated_at = datetime.utcnow() # Manually update timestamp
        db.session.commit()
        return self

    @staticmethod
    def get_all_customers():
        """
        Retrieves all customer records from the database.
        Returns:
            list[Customer]: A list of all Customer objects.
        """
        return Customer.query.all()

    @staticmethod
    def get_customer_by_id(customer_id):
        """
        Retrieves a customer by their customer_id.
        Args:
            customer_id (str): The UUID of the customer.
        Returns:
            Customer: The Customer object if found, otherwise None.
        """
        return Customer.query.get(customer_id)

    @staticmethod
    def get_duplicate_customers():
        """
        Identifies and returns potential duplicate customer records based on shared unique identifiers.
        This implementation finds customers where any of their unique identifiers (mobile, PAN, Aadhaar, UCID, LAN)
        are present in more than one customer record. This is a simplified approach for FR32.
        A dedicated deduplication service would handle the full complexity of FR3, FR4, FR5, FR6.
        Returns:
            list[Customer]: A list of Customer objects identified as potential duplicates.
        """
        # Subquery to find mobile numbers that appear more than once
        duplicate_mobiles = db.session.query(Customer.mobile_number).\
            group_by(Customer.mobile_number).\
            having(db.func.count(Customer.mobile_number) > 1).\
            filter(Customer.mobile_number.isnot(None)).subquery()

        # Subquery to find PAN numbers that appear more than once
        duplicate_pans = db.session.query(Customer.pan_number).\
            group_by(Customer.pan_number).\
            having(db.func.count(Customer.pan_number) > 1).\
            filter(Customer.pan_number.isnot(None)).subquery()

        # Subquery to find Aadhaar numbers that appear more than once
        duplicate_aadhaars = db.session.query(Customer.aadhaar_number).\
            group_by(Customer.aadhaar_number).\
            having(db.func.count(Customer.aadhaar_number) > 1).\
            filter(Customer.aadhaar_number.isnot(None)).subquery()

        # Subquery to find UCID numbers that appear more than once
        duplicate_ucids = db.session.query(Customer.ucid_number).\
            group_by(Customer.ucid_number).\
            having(db.func.count(Customer.ucid_number) > 1).\
            filter(Customer.ucid_number.isnot(None)).subquery()

        # Subquery to find Loan Application Numbers that appear more than once
        duplicate_lans = db.session.query(Customer.loan_application_number).\
            group_by(Customer.loan_application_number).\
            having(db.func.count(Customer.loan_application_number) > 1).\
            filter(Customer.loan_application_number.isnot(None)).subquery()

        # Find customers whose mobile_number, pan_number, aadhaar_number, ucid_number, or loan_application_number
        # is present in the respective duplicate subquery results.
        duplicates = Customer.query.filter(
            db.or_(
                Customer.mobile_number.in_(duplicate_mobiles),
                Customer.pan_number.in_(duplicate_pans),
                Customer.aadhaar_number.in_(duplicate_aadhaars),
                Customer.ucid_number.in_(duplicate_ucids),
                Customer.loan_application_number.in_(duplicate_lans)
            )
        ).all()
        
        return duplicates

    @staticmethod
    def get_unique_customers():
        """
        Returns customers identified as unique. This is a simplified inverse of get_duplicate_customers
        for the purpose of FR33. In a full CDP, unique customers would be the result of a canonicalization
        process after deduplication.
        Returns:
            list[Customer]: A list of Customer objects identified as unique.
        """
        # Get the IDs of customers identified as duplicates by the simplified logic
        duplicate_customer_ids = [c.customer_id for c in Customer.get_duplicate_customers()]
        
        # Return customers whose IDs are NOT in the duplicate list
        return Customer.query.filter(Customer.customer_id.notin_(duplicate_customer_ids)).all()