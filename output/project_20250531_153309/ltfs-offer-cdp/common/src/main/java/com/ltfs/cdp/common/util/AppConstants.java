package com.ltfs.cdp.common.util;

/**
 * AppConstants class defines application-wide constants used across the LTFS Offer CDP system.
 * These constants help in maintaining consistency and avoiding magic strings/numbers throughout the codebase.
 * They cover various aspects like API paths, common statuses, deduplication logic, validation messages,
 * system identifiers, event names for the event-driven architecture, and date/time formats.
 */
public final class AppConstants {

    /**
     * Private constructor to prevent instantiation of this utility class.
     * Utility classes, which only contain static members, should not be instantiated.
     */
    private AppConstants() {
        // SonarQube: Add a private constructor to hide the implicit public one.
    }

    // --- API & Endpoint Constants ---
    /**
     * Base path for all API endpoints, ensuring versioning and consistency.
     */
    public static final String API_BASE_PATH = "/api/v1";
    /**
     * API path for customer-related operations.
     */
    public static final String CUSTOMER_API_PATH = API_BASE_PATH + "/customers";
    /**
     * API path for offer-related operations.
     */
    public static final String OFFER_API_PATH = API_BASE_PATH + "/offers";
    /**
     * API path for campaign-related operations.
     */
    public static final String CAMPAIGN_API_PATH = API_BASE_PATH + "/campaigns";
    /**
     * API path for deduplication-related operations.
     */
    public static final String DEDUPE_API_PATH = API_BASE_PATH + "/deduplication";

    // --- Common Statuses & Types ---
    /**
     * Generic status indicating an active state.
     */
    public static final String STATUS_ACTIVE = "ACTIVE";
    /**
     * Generic status indicating an inactive state.
     */
    public static final String STATUS_INACTIVE = "INACTIVE";
    /**
     * Generic status indicating a pending state, awaiting further processing or approval.
     */
    public static final String STATUS_PENDING = "PENDING";
    /**
     * Generic status indicating a successful operation or state.
     */
    public static final String STATUS_SUCCESS = "SUCCESS";
    /**
     * Generic status indicating a failed operation or state.
     */
    public static final String STATUS_FAILED = "FAILED";

    // --- Deduplication Constants ---
    /**
     * Deduplication status indicating that a match was found for the entity.
     */
    public static final String DEDUPE_STATUS_MATCH_FOUND = "MATCH_FOUND";
    /**
     * Deduplication status indicating that no match was found for the entity.
     */
    public static final String DEDUPE_STATUS_NO_MATCH = "NO_MATCH";
    /**
     * Deduplication status indicating that the entity has been processed by the deduplication logic.
     */
    public static final String DEDUPE_STATUS_PROCESSED = "PROCESSED";
    /**
     * Deduplication status indicating that the entity was excluded from a specific deduplication run
     * (e.g., top-up loans deduped only within their own category).
     */
    public static final String DEDUPE_STATUS_EXCLUDED = "EXCLUDED";

    /**
     * Identifier for deduplication performed against the 'live book' (Customer 360).
     */
    public static final String DEDUPE_TYPE_LIVE_BOOK = "LIVE_BOOK";
    /**
     * Identifier for deduplication specific to Top-up Loan offers.
     */
    public static final String DEDUPE_TYPE_TOP_UP_LOAN = "TOP_UP_LOAN";

    // --- Validation Constants ---
    /**
     * Prefix for validation error codes or messages.
     */
    public static final String VALIDATION_ERROR_PREFIX = "VALIDATION_ERROR_";
    /**
     * Common validation message for fields that cannot be null.
     */
    public static final String VALIDATION_MESSAGE_NOT_NULL = "Field cannot be null.";
    /**
     * Common validation message for fields that cannot be empty.
     */
    public static final String VALIDATION_MESSAGE_NOT_EMPTY = "Field cannot be empty.";
    /**
     * Common validation message for fields with an invalid format.
     */
    public static final String VALIDATION_MESSAGE_INVALID_FORMAT = "Invalid format.";
    /**
     * Common validation message for fields with an invalid length.
     */
    public static final String VALIDATION_MESSAGE_INVALID_LENGTH = "Invalid length.";

    // --- System & Source Identifiers ---
    /**
     * Identifier for the Offermart system, a source of data for CDP.
     */
    public static final String SYSTEM_OFFERMART = "OFFERMART";
    /**
     * Identifier for the CDP (Customer Data Platform) system itself.
     */
    public static final String SYSTEM_CDP = "CDP";
    /**
     * Identifier for the Customer 360 system, referred to as the 'live book' for deduplication.
     */
    public static final String SYSTEM_CUSTOMER_360 = "CUSTOMER_360";

    // --- Event Bus / Messaging Constants (for Event-Driven Architecture) ---
    /**
     * Event name for when a customer profile has been updated.
     */
    public static final String EVENT_CUSTOMER_PROFILE_UPDATED = "customer.profile.updated";
    /**
     * Event name for when a new offer has been generated.
     */
    public static final String EVENT_OFFER_GENERATED = "offer.generated";
    /**
     * Event name for when a deduplication process has been initiated.
     */
    public static final String EVENT_DEDUPLICATION_INITIATED = "deduplication.initiated";
    /**
     * Event name for when a deduplication process has been completed.
     */
    public static final String EVENT_DEDUPLICATION_COMPLETED = "deduplication.completed";
    /**
     * Event name for when data validation fails during ingestion or processing.
     */
    public static final String EVENT_DATA_VALIDATION_FAILED = "data.validation.failed";
    /**
     * Event name for when an offer has been finalized after all checks, including deduplication.
     */
    public static final String EVENT_OFFER_FINALIZED = "offer.finalized";

    // --- Date and Time Formats ---
    /**
     * Standard date format: YYYY-MM-DD.
     */
    public static final String DATE_FORMAT_YYYY_MM_DD = "yyyy-MM-dd";
    /**
     * Standard datetime format: YYYY-MM-DD HH:MM:SS.
     */
    public static final String DATETIME_FORMAT_YYYY_MM_DD_HH_MM_SS = "yyyy-MM-dd HH:mm:ss";
    /**
     * ISO 8601 datetime format with milliseconds and timezone offset (e.g., 2023-10-27T10:00:00.000+05:30).
     */
    public static final String DATETIME_FORMAT_ISO_8601 = "yyyy-MM-dd'T'HH:mm:ss.SSSXXX";

    // --- Security Constants (Common headers/prefixes) ---
    /**
     * HTTP header name for authorization tokens.
     */
    public static final String AUTHORIZATION_HEADER = "Authorization";
    /**
     * Prefix for Bearer tokens in the Authorization header.
     */
    public static final String BEARER_TOKEN_PREFIX = "Bearer ";

    // --- Performance/Configuration related (Common values for pagination, etc.) ---
    /**
     * Default number of items per page for paginated API responses.
     */
    public static final int DEFAULT_PAGE_SIZE = 10;
    /**
     * Maximum allowed number of items per page for paginated API responses.
     */
    public static final int MAX_PAGE_SIZE = 100;
}