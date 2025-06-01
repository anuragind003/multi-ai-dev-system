package com.ltfs.cdp.campaign.repository;

import com.ltfs.cdp.campaign.model.Campaign;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

/**
 * Spring Data JPA repository for the {@link Campaign} entity.
 * This interface extends {@link JpaRepository} to provide standard
 * CRUD (Create, Read, Update, Delete) operations and pagination/sorting
 * capabilities for Campaign entities.
 *
 * <p>The primary key type for the Campaign entity is assumed to be {@code Long}.</p>
 *
 * <p>This repository is part of the `campaign-service` microservice within the
 * LTFS Offer CDP project, responsible for managing campaign-related data.</p>
 */
@Repository
public interface CampaignRepository extends JpaRepository<Campaign, Long> {

    // JpaRepository provides common methods like:
    // - save(S entity): Saves a given entity.
    // - findById(ID id): Retrieves an entity by its ID.
    // - findAll(): Returns all instances of the type.
    // - delete(T entity): Deletes a given entity.
    // - count(): Returns the number of entities available.

    // Custom query methods can be added here if specific business logic
    // requires finding campaigns by attributes other than their ID,
    // e.g., findByName(String name), findByStatus(CampaignStatus status), etc.
    // For example:
    // Optional<Campaign> findByCampaignName(String campaignName);
    // List<Campaign> findByStatus(String status);
}