package com.ltfs.cdp.common.exception;

/**
 * Custom exception to be thrown when a requested resource is not found.
 * This is an unchecked exception, meaning it extends {@link RuntimeException}.
 * It is typically used in service or repository layers to indicate that an entity
 * or data record could not be located based on the provided criteria.
 * <p>
 * In a Spring Boot application, this exception can be caught by a global
 * exception handler (e.g., using {@code @ControllerAdvice}) and mapped
 * to an appropriate HTTP status code, such as {@code HttpStatus.NOT_FOUND (404)}.
 * This approach allows for clean separation of concerns, where business logic
 * throws a domain-specific exception, and the web layer handles the HTTP response mapping.
 * </p>
 */
public class ResourceNotFoundException extends RuntimeException {

    /**
     * Constructs a new {@code ResourceNotFoundException} with {@code null} as its
     * detail message. The cause is not initialized, and may subsequently be
     * initialized by a call to {@link Throwable#initCause(Throwable)}.
     */
    public ResourceNotFoundException() {
        super();
    }

    /**
     * Constructs a new {@code ResourceNotFoundException} with the specified detail message.
     * The cause is not initialized, and may subsequently be initialized by a
     * call to {@link Throwable#initCause(Throwable)}.
     *
     * @param message the detail message. The detail message is saved for
     *                later retrieval by the {@link Throwable#getMessage()} method.
     */
    public ResourceNotFoundException(String message) {
        super(message);
    }

    /**
     * Constructs a new {@code ResourceNotFoundException} with the specified detail message and
     * cause.
     * <p>Note that the detail message associated with {@code cause} is <i>not</i>
     * automatically incorporated in this exception's detail message.
     *
     * @param message the detail message (which is saved for later retrieval by the
     *                {@link Throwable#getMessage()} method).
     * @param cause   the cause (which is saved for later retrieval by the
     *                {@link Throwable#getCause()} method). (A {@code null} value is
     *                permitted, and indicates that the cause is nonexistent or
     *                unknown.)
     */
    public ResourceNotFoundException(String message, Throwable cause) {
        super(message, cause);
    }

    /**
     * Constructs a new {@code ResourceNotFoundException} with the specified cause and a
     * detail message of {@code (cause==null ? null : cause.toString())}
     * (which typically contains the class and detail message of {@code cause}).
     * This constructor is useful for exceptions that are little more than
     * wrappers for other throwables (for example, {@link
     * java.security.PrivilegedActionException}).
     *
     * @param cause the cause (which is saved for later retrieval by the
     *              {@link Throwable#getCause()} method). (A {@code null} value is
     *              permitted, and indicates that the cause is nonexistent or
     *              unknown.)
     */
    public ResourceNotFoundException(Throwable cause) {
        super(cause);
    }

    /**
     * Constructs a new {@code ResourceNotFoundException} with the specified detail
     * message, cause, suppression enabled or disabled, and writable stack
     * trace enabled or disabled.
     *
     * @param message            the detail message.
     * @param cause              the cause. (A {@code null} value is permitted, and
     *                           indicates that the cause is nonexistent or unknown.)
     * @param enableSuppression  whether or not suppression is enabled or disabled
     * @param writableStackTrace whether or not the stack trace should be
     *                           writable
     */
    public ResourceNotFoundException(String message, Throwable cause, boolean enableSuppression, boolean writableStackTrace) {
        super(message, cause, enableSuppression, writableStackTrace);
    }
}