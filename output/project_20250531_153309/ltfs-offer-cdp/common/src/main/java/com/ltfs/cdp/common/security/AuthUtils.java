package com.ltfs.cdp.common.security;

import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;

import java.util.Collection;
import java.util.Collections;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Utility class for common authentication and authorization operations within the LTFS Offer CDP system.
 * This class provides convenient static methods to access details of the currently authenticated user
 * from Spring Security's SecurityContext.
 *
 * It helps in retrieving user information like username, user ID, and roles, and checking
 * for specific role permissions.
 */
public final class AuthUtils {

    // Private constructor to prevent instantiation of this utility class.
    // Utility classes should not be instantiated.
    private AuthUtils() {
        // SonarQube: Add a private constructor to hide the implicit public one.
    }

    /**
     * Retrieves the current {@link Authentication} object from the Spring Security context.
     * This method ensures that the retrieved authentication is not null, is authenticated,
     * and does not represent an anonymous user.
     *
     * @return An {@link Optional} containing the {@link Authentication} object if a valid
     *         authenticated user is present in the security context, otherwise an empty {@link Optional}.
     */
    public static Optional<Authentication> getCurrentAuthentication() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();

        // Check if authentication object exists, is authenticated, and is not an anonymous user.
        // "anonymousUser" is the default principal name for unauthenticated users in Spring Security.
        if (authentication == null || !authentication.isAuthenticated() || "anonymousUser".equals(authentication.getPrincipal())) {
            return Optional.empty();
        }
        return Optional.of(authentication);
    }

    /**
     * Retrieves the username of the currently authenticated user.
     * This typically corresponds to the principal's name as returned by {@link Authentication#getName()}.
     *
     * @return An {@link Optional} containing the username (String) if a user is authenticated,
     *         otherwise an empty {@link Optional}.
     */
    public static Optional<String> getCurrentUsername() {
        return getCurrentAuthentication()
                .map(Authentication::getName); // getName() typically returns the username
    }

    /**
     * Retrieves the principal object of the currently authenticated user.
     * The principal object can be a {@link UserDetails} instance (common with form-based login)
     * or a custom principal object (e.g., a JWT token object in a resource server setup).
     *
     * @param <T> The expected type of the principal object.
     * @return An {@link Optional} containing the principal object if a user is authenticated,
     *         otherwise an empty {@link Optional}.
     */
    @SuppressWarnings("unchecked") // Suppress warning for casting principal to T, as type is determined by caller.
    public static <T> Optional<T> getCurrentPrincipal() {
        return getCurrentAuthentication()
                .map(authentication -> (T) authentication.getPrincipal());
    }

    /**
     * Retrieves the user ID of the currently authenticated user.
     * This method first attempts to extract the username from a {@link UserDetails} principal.
     * If the principal is not a {@link UserDetails} instance, it falls back to using the
     * username obtained via {@link Authentication#getName()}.
     * In many systems, the username serves as the unique user identifier.
     *
     * @return An {@link Optional} containing the user ID (String) if a user is authenticated,
     *         otherwise an empty {@link Optional}.
     */
    public static Optional<String> getCurrentUserId() {
        return getCurrentPrincipal()
                .filter(principal -> principal instanceof UserDetails) // Check if principal is UserDetails
                .map(principal -> ((UserDetails) principal).getUsername()) // If so, use UserDetails's username
                .or(AuthUtils::getCurrentUsername); // Fallback to Authentication.getName() if not UserDetails
    }

    /**
     * Retrieves the roles/authorities of the currently authenticated user.
     * The roles are typically prefixed with "ROLE_" (e.g., "ROLE_ADMIN", "ROLE_USER").
     *
     * @return A {@link Set} of role names (Strings) if a user is authenticated,
     *         otherwise an empty set. The set contains the string representation of each granted authority.
     */
    public static Set<String> getCurrentUserRoles() {
        return getCurrentAuthentication()
                .map(Authentication::getAuthorities) // Get collection of GrantedAuthority
                .map(authorities -> authorities.stream()
                        .map(GrantedAuthority::getAuthority) // Map to authority string
                        .collect(Collectors.toSet())) // Collect into a Set
                .orElse(Collections.emptySet()); // Return empty set if no authentication
    }

    /**
     * Checks if the currently authenticated user has a specific role.
     * The role string should match the exact authority granted (e.g., "ROLE_ADMIN").
     *
     * @param role The role name (String) to check for.
     * @return {@code true} if the user has the specified role, {@code false} otherwise
     *         (including cases where no user is authenticated).
     */
    public static boolean hasRole(String role) {
        return getCurrentUserRoles().contains(role);
    }

    /**
     * Checks if the currently authenticated user has any of the specified roles.
     * This is useful for checking if a user belongs to a group of roles.
     *
     * @param roles A {@link Collection} of role names (Strings) to check against.
     * @return {@code true} if the user has at least one of the specified roles, {@code false} otherwise.
     */
    public static boolean hasAnyRole(Collection<String> roles) {
        Set<String> currentUserRoles = getCurrentUserRoles();
        return roles.stream().anyMatch(currentUserRoles::contains);
    }

    /**
     * Checks if the currently authenticated user is an anonymous user or if no user is authenticated.
     * This is a convenience method to quickly determine if the current context represents an unauthenticated state.
     *
     * @return {@code true} if the user is anonymous or no user is authenticated, {@code false} otherwise.
     */
    public static boolean isAnonymousUser() {
        return !getCurrentAuthentication().isPresent();
    }
}