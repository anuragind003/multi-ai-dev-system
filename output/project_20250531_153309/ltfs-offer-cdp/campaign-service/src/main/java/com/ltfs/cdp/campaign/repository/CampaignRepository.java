package com.ltfs.cdp.campaign.repository;

import com.ltfs.cdp.campaign.model.Campaign;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

/**
 * Repository interface for {@link Campaign} entities.
 * This interface extends {@link JpaRepository} to provide standard CRUD operations
 * and pagination/sorting capabilities for Campaign entities.
 *
 * <p>Spring Data JPA automatically generates the implementation for this interface
 * at runtime based on the method names and the entity type.</p>
 */
@Repository
public interface CampaignRepository extends JpaRepository<Campaign, Long> {

    // Custom query methods can be added here if needed, for example:
    // List<Campaign> findByStatus(String status);
    // Optional<Campaign> findByCampaignCode(String campaignCode);
}