package com.ltfs.cdp.campaign.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.GenericGenerator;

import javax.persistence.*;
import java.time.Instant;
import java.util.UUID;

/**
 * Entity for storing campaign performance metrics.
 * This model represents a single metric associated with a specific campaign,
 * allowing for tracking various performance indicators over time.
 * It is designed to be stored in a PostgreSQL database as part of the
 * LTFS Offer CDP's campaign-service.
 */
@Entity
@Table(name = "campaign_metrics")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CampaignMetric {

    /**
     * Unique identifier for the campaign metric record.
     * This is the primary key and is automatically generated as a UUID.
     * Using UUIDs is beneficial in distributed systems for unique identification
     * without relying on sequential database IDs.
     */
    @Id
    @GeneratedValue(generator = "UUID")
    @GenericGenerator(name = "UUID", strategy = "org.hibernate.id.UUIDGenerator")
    @Column(name = "id", updatable = false, nullable = false)
    private UUID id;

    /**
     * The unique identifier of the campaign to which this metric belongs.
     * In a microservices architecture, this typically refers to the ID of a Campaign
     * entity managed by the same or another service. It acts as a logical foreign key.
     */
    @Column(name = "campaign_id", nullable = false)
    private UUID campaignId;

    /**
     * The name of the performance metric. Examples include "Offers Sent", "Offers Accepted",
     * "Conversion Rate", "Click-Through Rate", "Revenue Generated", "Impressions", etc.
     * This field allows for flexible tracking of various metric types without schema changes.
     */
    @Column(name = "metric_name", nullable = false, length = 100)
    private String metricName;

    /**
     * The numerical value of the performance metric.
     * Using {@code Double} provides flexibility to store various types of values,
     * including integers, percentages, and decimal numbers (e.g., monetary values, rates).
     */
    @Column(name = "metric_value", nullable = false)
    private Double metricValue;

    /**
     * Timestamp when this specific metric value was first recorded or calculated.
     * This can represent the start of a period for which the metric is valid,
     * or the exact time of a snapshot. It is automatically set on creation.
     */
    @Column(name = "recorded_at", nullable = false)
    private Instant recordedAt;

    /**
     * Timestamp when this campaign metric record was last updated.
     * This is particularly useful for aggregate metrics that are periodically refreshed,
     * allowing tracking of the freshness of the data. It is automatically updated on modification.
     */
    @Column(name = "last_updated", nullable = false)
    private Instant lastUpdated;

    /**
     * An optional description providing more context or details about the metric.
     * This can be used to clarify how the metric is calculated or what it represents.
     */
    @Column(name = "description", length = 500)
    private String description;

    /**
     * Lifecycle callback method executed before a new entity is persisted (saved) to the database.
     * It automatically sets the {@code recordedAt} and {@code lastUpdated} timestamps to the current time.
     */
    @PrePersist
    protected void onCreate() {
        Instant now = Instant.now();
        this.recordedAt = now;
        this.lastUpdated = now;
    }

    /**
     * Lifecycle callback method executed before an existing entity is updated in the database.
     * It automatically updates the {@code lastUpdated} timestamp to the current time,
     * indicating when the record was last modified.
     */
    @PreUpdate
    protected void onUpdate() {
        this.lastUpdated = Instant.now();
    }
}