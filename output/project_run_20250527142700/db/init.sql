-- Ensure the uuid-ossp extension is available for UUID generation
-- This extension provides functions to generate UUIDs, which are used for primary keys.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop tables in reverse order of dependency to avoid foreign key constraint issues
-- CASCADE ensures that any dependent objects (like foreign keys) are also dropped.
DROP TABLE IF EXISTS campaigns CASCADE;
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS offer_history CASCADE;
DROP TABLE IF EXISTS offers CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- Create customers table
-- Stores de-duplicated customer profiles.
CREATE TABLE customers (
    customer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mobile_number VARCHAR(20) UNIQUE,
    pan_number VARCHAR(10) UNIQUE,
    aadhaar_number VARCHAR(12) UNIQUE,
    ucid_number VARCHAR(50) UNIQUE,
    customer_360_id VARCHAR(50), -- For integration with Customer 360
    is_dnd BOOLEAN DEFAULT FALSE, -- Do Not Disturb flag (FR24)
    segment VARCHAR(50), -- Customer segments like C1-C8 (FR15, FR21)
    attributes JSONB, -- For other flexible customer attributes (FR15)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for frequently queried columns on customers table
CREATE INDEX idx_customers_mobile_number ON customers (mobile_number);
CREATE INDEX idx_customers_pan_number ON customers (pan_number);
CREATE INDEX idx_customers_aadhaar_number ON customers (aadhaar_number);
CREATE INDEX idx_customers_ucid_number ON customers (ucid_number);
CREATE INDEX idx_customers_is_dnd ON customers (is_dnd);
CREATE INDEX idx_customers_segment ON customers (segment);


-- Create offers table
-- Stores details of various loan offers associated with customers.
CREATE TABLE offers (
    offer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE, -- Link to customer, delete offers if customer is deleted
    source_offer_id VARCHAR(100), -- Original ID from Offermart/E-aggregator (FR8, FR10)
    offer_type VARCHAR(50), -- 'Fresh', 'Enrich', 'New-old', 'New-new' (FR17)
    offer_status VARCHAR(50), -- 'Active', 'Inactive', 'Expired' (FR16)
    propensity VARCHAR(50), -- Analytics-defined propensity (FR19)
    loan_application_number VARCHAR(100), -- Loan Application Number (LAN) (FR13, FR36)
    valid_until TIMESTAMP WITH TIME ZONE, -- Offer expiry date
    source_system VARCHAR(50), -- 'Offermart', 'E-aggregator' (FR8, FR10)
    channel VARCHAR(50), -- For attribution logic (FR22)
    is_duplicate BOOLEAN DEFAULT FALSE, -- Flagged by deduplication process (FR1, FR18)
    original_offer_id UUID REFERENCES offers(offer_id) ON DELETE SET NULL, -- Points to the offer it duplicated/enriched (FR18)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for frequently queried columns on offers table
CREATE INDEX idx_offers_customer_id ON offers (customer_id);
CREATE INDEX idx_offers_offer_status ON offers (offer_status);
CREATE INDEX idx_offers_valid_until ON offers (valid_until);
CREATE INDEX idx_offers_loan_application_number ON offers (loan_application_number);
CREATE INDEX idx_offers_is_duplicate ON offers (is_duplicate);
CREATE INDEX idx_offers_source_system ON offers (source_system);


-- Create offer_history table
-- Maintains a history of offer status changes (FR20, NFR10).
CREATE TABLE offer_history (
    history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    offer_id UUID NOT NULL REFERENCES offers(offer_id) ON DELETE CASCADE, -- Link to offer, delete history if offer is deleted
    status_change_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    change_reason TEXT
);

-- Add index for offer_history table
CREATE INDEX idx_offer_history_offer_id ON offer_history (offer_id);
CREATE INDEX idx_offer_history_status_change_date ON offer_history (status_change_date);


-- Create events table
-- Stores various customer and loan journey events from Moengage and LOS (FR23, FR25, FR26, FR27).
CREATE TABLE events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES customers(customer_id) ON DELETE CASCADE, -- Link to customer, delete events if customer is deleted
    offer_id UUID REFERENCES offers(offer_id) ON DELETE CASCADE, -- Link to offer, delete events if offer is deleted
    event_type VARCHAR(100) NOT NULL, -- e.g., SMS_SENT, EKYC_ACHIEVED, JOURNEY_LOGIN
    event_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    source_system VARCHAR(50) NOT NULL, -- 'Moengage', 'LOS'
    event_details JSONB -- Raw event payload for flexibility
);

-- Add indexes for events table
CREATE INDEX idx_events_customer_id ON events (customer_id);
CREATE INDEX idx_events_offer_id ON events (offer_id);
CREATE INDEX idx_events_event_type ON events (event_type);
CREATE INDEX idx_events_event_timestamp ON events (event_timestamp);
CREATE INDEX idx_events_source_system ON events (source_system);


-- Create campaigns table
-- Stores metadata and metrics for marketing campaigns (FR34, FR35).
CREATE TABLE campaigns (
    campaign_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_name VARCHAR(255) NOT NULL,
    campaign_date DATE NOT NULL,
    campaign_unique_identifier VARCHAR(100) UNIQUE NOT NULL,
    attempted_count INTEGER DEFAULT 0,
    sent_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    success_rate NUMERIC(5,2) DEFAULT 0.0, -- Percentage
    conversion_rate NUMERIC(5,2) DEFAULT 0.0, -- Percentage
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for campaigns table
CREATE INDEX idx_campaigns_campaign_date ON campaigns (campaign_date);
CREATE INDEX idx_campaigns_campaign_unique_identifier ON campaigns (campaign_unique_identifier);


-- Function to automatically update the 'updated_at' column on row modification
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to tables that have an 'updated_at' column
CREATE TRIGGER update_customers_updated_at
BEFORE UPDATE ON customers
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_offers_updated_at
BEFORE UPDATE ON offers
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_campaigns_updated_at
BEFORE UPDATE ON campaigns
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();