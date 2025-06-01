package com.ltfs.cdp.datavalidation.producer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import org.springframework.stereotype.Component;
import org.springframework.util.concurrent.ListenableFuture;
import org.springframework.util.concurrent.ListenableFutureCallback;

/**
 * Component responsible for publishing validated customer data to a Kafka topic.
 * This data is intended for further processing by other services within the CDP ecosystem,
 * such as the Customer Service for deduplication or the Offer Finalization Service.
 *
 * It leverages Spring Kafka's KafkaTemplate for asynchronous message sending.
 */
@Component
public class ValidatedDataProducer {

    private static final Logger log = LoggerFactory.getLogger(ValidatedDataProducer.class);

    private final KafkaTemplate<String, String> kafkaTemplate;

    /**
     * The Kafka topic name where validated data will be published.
     * This value is injected from application properties (e.g., application.yml or application.properties).
     * Example property: kafka.topics.validated-data=cdp.validated.customer.data
     */
    @Value("${kafka.topics.validated-data}")
    private String validatedDataTopic;

    /**
     * Constructs a ValidatedDataProducer with the necessary KafkaTemplate.
     * Spring automatically injects the configured KafkaTemplate.
     *
     * @param kafkaTemplate The KafkaTemplate instance used for sending messages to Kafka.
     */
    public ValidatedDataProducer(KafkaTemplate<String, String> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    /**
     * Publishes validated customer data to the configured Kafka topic.
     * The data is expected to be a JSON string representing the validated customer record.
     * This method sends the message asynchronously and logs the outcome (success or failure).
     *
     * @param validatedDataJson The validated customer data as a JSON string.
     *                          This string should represent a single, validated customer record
     *                          ready for further processing (e.g., deduplication).
     */
    public void publishValidatedData(String validatedDataJson) {
        if (validatedDataJson == null || validatedDataJson.trim().isEmpty()) {
            log.warn("Attempted to publish empty or null validated data to topic: {}. Skipping.", validatedDataTopic);
            return;
        }

        log.info("Attempting to publish validated data to topic: {}", validatedDataTopic);

        // Send the message to Kafka asynchronously.
        // The key is null here, implying round-robin distribution or custom partitioning based on Kafka configuration.
        // For ordered processing of specific customer data, a customer ID could be used as the key.
        ListenableFuture<SendResult<String, String>> future = kafkaTemplate.send(validatedDataTopic, validatedDataJson);

        // Add a callback to handle the result of the asynchronous send operation.
        future.addCallback(new ListenableFutureCallback<SendResult<String, String>>() {
            @Override
            public void onSuccess(SendResult<String, String> result) {
                // Log successful publication details.
                log.info("Successfully published validated data to topic: '{}', partition: {}, offset: {}. Payload snippet: {}",
                        result.getProducerRecord().topic(),
                        result.getRecordMetadata().partition(),
                        result.getRecordMetadata().offset(),
                        validatedDataJson.length() > 100 ? validatedDataJson.substring(0, 100) + "..." : validatedDataJson);
            }

            @Override
            public void onFailure(Throwable ex) {
                // Log failure details.
                // In a production system, consider implementing retry mechanisms,
                // sending to a dead-letter queue (DLQ), or alerting.
                log.error("Failed to publish validated data to topic: '{}'. Error: {}. Payload: {}",
                        validatedDataTopic, ex.getMessage(), validatedDataJson, ex);
            }
        });
    }
}