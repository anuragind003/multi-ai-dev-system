-- This script initializes the PostgreSQL database schema for the LTFS Offer Customer Data Platform (CDP).
-- It creates tables for customers, offers, events, campaign metrics, and ingestion logs,
-- based on the system design and functional requirements.

-- Enable the uuid-ossp extension for UUID generation.
-- This is a common practice in PostgreSQL for generating universally unique identifiers.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop tables in reverse order of dependency to avoid foreign key constraint errors
-- The CASCADE option ensures that any dependent objects (like foreign key constraints) are also dropped.
DROP TABLE IF EXISTS ingestion_logs CASCADE;
DROP TABLE IF EXISTS campaign_metrics CASCADE;
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS offers CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- Table: customers
-- Stores core customer profile data.
-- FR2: Provides a single profile view of the customer.
-- FR3, FR4, FR5, FR6: Unique constraints on identification fields support deduplication logic.
-- FR15, FR20: 'segment' column for customer attributes and segments.
-- FR23: 'dnd_flag' to prevent campaigns to DND customers.
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY DEFAULT uuid_generate_v4(), -- Unique identifier for the customer, generated as UUID
    mobile_number TEXT UNIQUE, -- Unique mobile number for deduplication
    pan_number TEXT UNIQUE,    -- Unique PAN number for deduplication
    aadhaar_number TEXT UNIQUE, -- Unique Aadhaar number for deduplication
    ucid_number TEXT UNIQUE,    -- Unique UCID number for deduplication
    loan_application_number TEXT UNIQUE, -- Unique previous loan application number for deduplication
    dnd_flag BOOLEAN DEFAULT FALSE, -- Flag to indicate Do Not Disturb status
    segment TEXT, -- Customer segment (e.g., C1-C8, analytics-prescribed segments)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- Timestamp when the record was created
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP  -- Timestamp when the record was last updated
);

-- Add indexes for frequently queried columns to improve performance
CREATE INDEX idx_customers_mobile_number ON customers (mobile_number);
CREATE INDEX idx_customers_pan_number ON customers (pan_number);
CREATE INDEX idx_customers_aadhaar_number ON customers (aadhaar_number);
CREATE INDEX idx_customers_ucid_number ON customers (ucid_number);
CREATE INDEX idx_customers_loan_application_number ON customers (loan_application_number);
CREATE INDEX idx_customers_segment ON customers (segment);
CREATE INDEX idx_customers_dnd_flag ON customers (dnd_flag);


-- Table: offers
-- Stores details of offers associated with customers.
-- FR16: 'offer_status' for managing offer lifecycle.
-- FR17: 'offer_type' for campaigning purposes.
-- FR18: 'propensity' values from Offermart.
-- FR19: 'created_at' for maintaining offer history (past 6 months).
-- FR41, FR42, FR43: 'start_date', 'end_date', 'offer_status', and 'loan_application_number' for offer expiry logic.
-- FR21: 'channel' for attribution logic.
CREATE TABLE offers (
    offer_id TEXT PRIMARY KEY DEFAULT uuid_generate_v4(), -- Unique identifier for the offer
    customer_id TEXT NOT NULL REFERENCES customers(customer_id), -- Foreign key linking to the customers table
    offer_type TEXT, -- Type of offer (e.g., 'Fresh', 'Enrich', 'New-old', 'New-new')
    offer_status TEXT, -- Current status of the offer (e.g., 'Active', 'Inactive', 'Expired', 'Journey Started')
    propensity TEXT, -- Propensity score/category from analytics
    start_date DATE, -- Date when the offer becomes active
    end_date DATE, -- Date when the offer expires
    channel TEXT, -- Channel or source of the offer (e.g., 'Insta', 'E-aggregator', 'Offermart')
    loan_application_number TEXT, -- Loan Application Number if a journey has started for this offer (FR14, FR43)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- Timestamp when the offer record was created
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP  -- Timestamp when the offer record was last updated
);

-- Add indexes for common query patterns on the offers table
CREATE INDEX idx_offers_customer_id ON offers (customer_id);
CREATE INDEX idx_offers_status ON offers (offer_status);
CREATE INDEX idx_offers_end_date ON offers (end_date);
CREATE INDEX idx_offers_type ON offers (offer_type);
CREATE INDEX idx_offers_loan_application_number ON offers (loan_application_number);


-- Table: events
-- Stores various customer interaction and application journey events.
-- FR22: Stores event data from Moengage and LOS.
-- FR24: Captures SMS event data.
-- FR25: Captures conversion data.
-- FR26: Captures application stage data.
CREATE TABLE events (
    event_id TEXT PRIMARY KEY DEFAULT uuid_generate_v4(), -- Unique identifier for the event
    customer_id TEXT NOT NULL REFERENCES customers(customer_id), -- Foreign key linking to the customers table
    event_type TEXT NOT NULL, -- Type of event (e.g., 'SMS_SENT', 'SMS_DELIVERED', 'SMS_CLICKED', 'EKYC_ACHIEVED', 'DISBURSEMENT', 'LOAN_LOGIN', 'BUREAU_CHECK', 'OFFER_DETAILS', 'BANK_DETAILS', 'E_SIGN')
    event_source TEXT NOT NULL, -- Source system of the event (e.g., 'Moengage', 'LOS', 'E-aggregator', 'CDP_INTERNAL')
    event_timestamp TIMESTAMP WITH TIME ZONE NOT NULL, -- Timestamp when the event occurred
    event_details JSONB, -- Flexible JSONB field for storing event-specific details (e.g., SMS content, loan amount, stage details)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- Timestamp when the event record was created
);

-- Add indexes for efficient querying of events
CREATE INDEX idx_events_customer_id ON events (customer_id);
CREATE INDEX idx_events_type ON events (event_type);
CREATE INDEX idx_events_source ON events (event_source);
CREATE INDEX idx_events_timestamp ON events (event_timestamp);


-- Table: campaign_metrics
-- Stores aggregated metrics for marketing campaigns.
-- FR30: Stores campaign metrics including attempted, sent, failed, conversion rates.
CREATE TABLE campaign_metrics (
    metric_id TEXT PRIMARY KEY DEFAULT uuid_generate_v4(), -- Unique identifier for the metric record
    campaign_unique_id TEXT UNIQUE NOT NULL, -- Unique identifier for the campaign
    campaign_name TEXT, -- Name of the campaign
    campaign_date DATE, -- Date of the campaign
    attempted_count INTEGER, -- Number of customers targeted in the campaign
    sent_success_count INTEGER, -- Number of messages/offers successfully sent
    failed_count INTEGER, -- Number of messages/offers that failed to send
    conversion_rate NUMERIC(5,2), -- Conversion rate for the campaign (e.g., 12.34 for 12.34%)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- Timestamp when the metric record was created
);

-- Add index for campaign date for reporting
CREATE INDEX idx_campaign_metrics_campaign_date ON campaign_metrics (campaign_date);


-- Table: ingestion_logs
-- Logs details of data ingestion processes, particularly file uploads via the Admin Portal.
-- FR37: Records successful data uploads.
-- FR38: Records failed uploads with error descriptions.
CREATE TABLE ingestion_logs (
    log_id TEXT PRIMARY KEY DEFAULT uuid_generate_v4(), -- Unique identifier for the log entry
    file_name TEXT NOT NULL, -- Name of the uploaded file
    upload_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- Timestamp of the upload
    status TEXT NOT NULL, -- Status of the ingestion ('SUCCESS', 'FAILED', 'PROCESSING')
    success_count INTEGER DEFAULT 0, -- Number of records successfully processed from the file
    error_count INTEGER DEFAULT 0, -- Number of records that resulted in errors from the file
    error_description TEXT, -- Detailed error message if the upload failed or had errors
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- Timestamp when the log record was created
);

-- Add indexes for upload timestamp and status for log querying
CREATE INDEX idx_ingestion_logs_upload_timestamp ON ingestion_logs (upload_timestamp);
CREATE INDEX idx_ingestion_logs_status ON ingestion_logs (status);


-- Trigger function to automatically update the 'updated_at' column
-- This function is called before an UPDATE operation on tables that have an 'updated_at' column.
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply the trigger to the 'customers' table
CREATE TRIGGER update_customers_updated_at
BEFORE UPDATE ON customers
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Apply the trigger to the 'offers' table
CREATE TRIGGER update_offers_updated_at
BEFORE UPDATE ON offers
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Note on Data Retention (FR19, FR28, NFR8, NFR9):
-- The 'created_at' and 'updated_at' columns are included in relevant tables to support
-- the implementation of data retention policies (e.g., 6 months for offer history,
-- 3 months for all data in CDP before deletion).
-- The actual data deletion or archival logic will be handled by scheduled backend jobs
-- and is not part of this initial schema definition.