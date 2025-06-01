package com.ltfs.cdp.datavalidation.listener;

import com.ltfs.cdp.datavalidation.event.RawDataEvent;
import com.ltfs.cdp.datavalidation.service.RawDataValidationService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

/**
 * RawDataEventListener is a Spring component responsible for listening to
 * {@link RawDataEvent} instances. These events typically originate from
 * the Integration Service, carrying raw customer or offer data that needs
 * to be validated before further processing within the CDP system.
 *
 * Upon receiving an event, this listener delegates the actual data validation
 * and processing to the {@link RawDataValidationService}.
 */
@Component
public class RawDataEventListener {

    private static final Logger log = LoggerFactory.getLogger(RawDataEventListener.class);

    private final RawDataValidationService rawDataValidationService;

    /**
     * Constructs a new RawDataEventListener.
     * Spring's dependency injection automatically provides the required
     * {@link RawDataValidationService} instance.
     *
     * @param rawDataValidationService The service responsible for performing
     *                                 column-level validation and initial processing
     *                                 of raw data.
     */
    public RawDataEventListener(RawDataValidationService rawDataValidationService) {
        this.rawDataValidationService = rawDataValidationService;
    }

    /**
     * Handles the {@link RawDataEvent} published within the Spring application context.
     * This method is automatically invoked by Spring's event publishing mechanism
     * when a {@code RawDataEvent} is dispatched.
     *
     * It performs initial checks on the event payload and then delegates to the
     * {@link RawDataValidationService} for the core validation logic.
     * Robust error handling is included to log any issues during processing.
     *
     * @param event The {@link RawDataEvent} containing the raw data payload,
     *              source system information, and a unique event identifier.
     */
    @EventListener
    public void handleRawDataEvent(RawDataEvent event) {
        // Basic validation of the event object and its payload
        if (event == null) {
            log.warn("Received a null RawDataEvent. Skipping processing.");
            return;
        }

        // Extract relevant information for logging and processing
        String eventId = event.getEventId() != null ? event.getEventId() : "N/A";
        String sourceSystem = event.getSourceSystem() != null ? event.getSourceSystem() : "Unknown";
        String rawPayload = event.getPayload();

        if (rawPayload == null || rawPayload.isEmpty()) {
            log.warn("Received RawDataEvent [ID: {}, Source: {}] with null or empty payload. Skipping validation.",
                    eventId, sourceSystem);
            return;
        }

        log.info("Received RawDataEvent [ID: {}, Source: {}] for validation. Payload size: {} bytes.",
                eventId, sourceSystem, rawPayload.length());

        try {
            // Delegate the raw data validation and initial processing to the service layer.
            // The service will handle parsing the rawPayload (e.g., JSON) and applying
            // column-level validations as per functional requirements.
            rawDataValidationService.validateAndProcessRawData(rawPayload, sourceSystem, eventId);

            log.info("Successfully initiated validation for RawDataEvent [ID: {}, Source: {}].", eventId, sourceSystem);
        } catch (Exception e) {
            // Catching a general Exception to ensure no event processing failure goes unlogged.
            // In a production system, more specific exceptions might be caught and handled
            // differently (e.g., data parsing errors, validation rule failures).
            log.error("Error processing RawDataEvent [ID: {}, Source: {}]: {}. Full stack trace: ",
                    eventId, sourceSystem, e.getMessage(), e);
            // Depending on the business requirements, further actions could be taken here,
            // such as publishing a "validation failed" event, moving the event to a dead-letter queue,
            // or triggering an alert. For now, robust logging is sufficient.
        }
    }
}