package com.ltfs.cdp.integration.producer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import org.springframework.stereotype.Service;

import java.util.concurrent.CompletableFuture;

/**
 * Service responsible for publishing raw incoming data to a Kafka topic.
 * This data is typically intended for the Data Validation Service for initial processing
 * before further deduplication and enrichment.
 */
@Service
public class RawDataProducer {

    private static final Logger log = LoggerFactory.getLogger(RawDataProducer.class);

    // Kafka topic name for raw incoming data, injected from application properties.
    // Example: kafka.topic.raw-data=ltfs.cdp.raw-data-topic
    @Value("${kafka.topic.raw-data}")
    private String rawDataTopic;

    private final KafkaTemplate<String, String> kafkaTemplate;

    /**
     * Constructs a RawDataProducer with the given KafkaTemplate.
     * Spring automatically injects the configured KafkaTemplate.
     *
     * @param kafkaTemplate The KafkaTemplate instance used to send messages to Kafka.
     */
    public RawDataProducer(KafkaTemplate<String, String> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    /**
     * Publishes raw incoming data to the configured Kafka topic asynchronously.
     * The method returns a {@link CompletableFuture} which allows the caller to
     * react to the success or failure of the send operation.
     *
     * @param key     A unique key for the Kafka message. This key is crucial for
     *                partitioning and can be used for message ordering guarantees
     *                within a partition, or for log compaction. For raw data,
     *                this could be a unique identifier from the source system,
     *                a customer ID, or a generated UUID.
     * @param rawData The raw data payload as a String. This is expected to be
     *                the complete incoming record, typically in JSON or CSV format.
     * @return A {@link CompletableFuture} that completes with a {@link SendResult}
     *         on successful delivery, or completes exceptionally if the send fails.
     */
    public CompletableFuture<SendResult<String, String>> sendRawData(String key, String rawData) {
        log.info("Attempting to send raw data to Kafka topic '{}' with key: {}", rawDataTopic, key);

        // Send the message asynchronously. The KafkaTemplate returns a CompletableFuture.
        // This non-blocking approach is essential for high-throughput systems.
        CompletableFuture<SendResult<String, String>> future = kafkaTemplate.send(rawDataTopic, key, rawData);

        // Attach callbacks to the CompletableFuture for logging success or failure.
        // These callbacks execute when the future completes, either successfully or exceptionally.
        future.whenComplete((result, ex) -> {
            if (ex == null) {
                // Log successful send operation, including topic, partition, and offset for traceability.
                log.info("Successfully sent raw data with key '{}' to topic '{}' at offset {} in partition {}",
                        key,
                        result.getRecordMetadata().topic(),
                        result.getRecordMetadata().offset(),
                        result.getRecordMetadata().partition());
            } else {
                // Log failure to send data. This indicates an issue with Kafka broker,
                // network, or serialization. The exception provides details.
                log.error("Failed to send raw data with key '{}' to topic '{}' due to: {}",
                        key, rawDataTopic, ex.getMessage(), ex);
                // Depending on requirements, a retry mechanism or dead-letter queue
                // could be implemented here or by the Kafka client configuration.
            }
        });

        return future;
    }
}