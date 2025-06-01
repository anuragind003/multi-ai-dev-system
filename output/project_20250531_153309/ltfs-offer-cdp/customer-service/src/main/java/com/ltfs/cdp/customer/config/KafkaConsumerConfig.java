package com.ltfs.cdp.customer.config;

import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.annotation.EnableKafka;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.kafka.core.DefaultKafkaConsumerFactory;
import org.springframework.kafka.listener.DefaultErrorHandler;
import org.springframework.util.backoff.FixedBackOff;
import org.springframework.kafka.support.serializer.JsonDeserializer;

import java.util.HashMap;
import java.util.Map;

/**
 * KafkaConsumerConfig
 *
 * This class configures Kafka consumer properties for the customer-service.
 * It sets up the ConsumerFactory and ConcurrentKafkaListenerContainerFactory
 * required for listening to incoming data and validation events related to
 * customer and offer data within the LTFS Offer CDP system.
 *
 * Key configurations include:
 * - Bootstrap servers for connecting to Kafka.
 * - Group ID for consumer groups.
 * - Key and value deserializers (String for key, JSON for value).
 * - Error handling for robust message processing.
 */
@Configuration
@EnableKafka // Enables detection of @KafkaListener annotations throughout the application
public class KafkaConsumerConfig {

    @Value("${spring.kafka.bootstrap-servers}")
    private String bootstrapServers;

    @Value("${spring.kafka.consumer.group-id}")
    private String groupId;

    /**
     * Configures the Kafka ConsumerFactory.
     * This factory is responsible for creating Kafka Consumer instances.
     * It defines the essential properties for connecting to Kafka and
     * deserializing messages.
     *
     * @return A ConsumerFactory configured with essential Kafka consumer properties.
     */
    @Bean
    public ConsumerFactory<String, Object> consumerFactory() {
        Map<String, Object> props = new HashMap<>();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ConsumerConfig.GROUP_ID_CONFIG, groupId);
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class);
        // Use JsonDeserializer for value to automatically convert JSON messages to Java objects.
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, JsonDeserializer.class);
        // Configure JsonDeserializer to trust all packages. In a production environment,
        // it's highly recommended to specify trusted packages (e.g., "com.ltfs.cdp.customer.model.*")
        // for security reasons to prevent deserialization vulnerabilities.
        props.put(JsonDeserializer.TRUSTED_PACKAGES, "*");
        // Optionally, set auto-offset-reset to 'earliest' to consume from the beginning
        // if no offset is committed, or 'latest' to consume only new messages.
        // props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        // Enable auto commit of offsets (default is true). For more control and
        // at-least-once processing, set to false and manually commit offsets after successful processing.
        // props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "false");

        return new DefaultKafkaConsumerFactory<>(props);
    }

    /**
     * Configures the ConcurrentKafkaListenerContainerFactory.
     * This factory is used to create Kafka message listener containers,
     * which are responsible for consuming messages from Kafka topics concurrently.
     * It integrates with the ConsumerFactory and provides error handling capabilities.
     *
     * @param consumerFactory The ConsumerFactory to be used by the container.
     * @return A ConcurrentKafkaListenerContainerFactory configured for concurrent message consumption.
     */
    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, Object> kafkaListenerContainerFactory(
            ConsumerFactory<String, Object> consumerFactory) {
        ConcurrentKafkaListenerContainerFactory<String, Object> factory =
                new ConcurrentKafkaListenerContainerFactory<>();
        factory.setConsumerFactory(consumerFactory);

        // Configure a DefaultErrorHandler for robust message processing.
        // This handler will retry processing messages a fixed number of times
        // before giving up and logging the error. This prevents transient issues
        // from causing message loss or unhandled exceptions.
        // FixedBackOff(interval, maxAttempts): Retries 3 times with a 1-second delay between attempts.
        factory.setCommonErrorHandler(new DefaultErrorHandler(new FixedBackOff(1000L, 3L)));

        // Set concurrency if needed. This determines how many listener threads are created
        // for a single @KafkaListener method. This can improve throughput.
        // factory.setConcurrency(3); // Example: 3 listener threads for a topic partition

        return factory;
    }
}