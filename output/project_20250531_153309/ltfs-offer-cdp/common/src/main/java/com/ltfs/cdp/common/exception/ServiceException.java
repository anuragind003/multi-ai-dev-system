package com.ltfs.cdp.common.exception;

/**
 * {@code ServiceException} is a generic base exception for business logic errors
 * within the LTFS Offer CDP system.
 * <p>
 * This exception is intended to be used when an operation fails due to a business rule
 * violation or an expected error condition that is part of the application's domain logic.
 * It extends {@link RuntimeException} to avoid forcing calling methods to declare
 * checked exceptions, aligning with common Spring Boot practices for service layer exceptions.
 * </p>
 * <p>
 * Specific business exceptions should extend this class to provide more granular
 * error handling and clearer error messages.
 * </p>
 */
public class ServiceException extends RuntimeException {

    /**
     * Constructs a new {@code ServiceException} with {@code null} as its detail message.
     * The cause is not initialized, and may subsequently be initialized by a call to
     * {@link Throwable#initCause(Throwable)}.
     */
    public ServiceException() {
        super();
    }

    /**
     * Constructs a new {@code ServiceException} with the specified detail message.
     * The cause is not initialized, and may subsequently be initialized by a call to
     * {@link Throwable#initCause(Throwable)}.
     *
     * @param message the detail message (which is saved for later retrieval by the
     *                {@link Throwable#getMessage()} method).
     */
    public ServiceException(String message) {
        super(message);
    }

    /**
     * Constructs a new {@code ServiceException} with the specified detail message and
     * cause.
     * <p>Note that the detail message associated with {@code cause} is <i>not</i>
     * automatically incorporated in this exception's detail message.</p>
     *
     * @param message the detail message (which is saved for later retrieval by the
     *                {@link Throwable#getMessage()} method).
     * @param cause   the cause (which is saved for later retrieval by the
     *                {@link Throwable#getCause()} method). (A {@code null} value
     *                is permitted, and indicates that the cause is nonexistent or
     *                unknown.)
     */
    public ServiceException(String message, Throwable cause) {
        super(message, cause);
    }

    /**
     * Constructs a new {@code ServiceException} with the specified cause and a
     * detail message of {@code (cause==null ? null : cause.toString())}
     * (which typically contains the class and detail message of {@code cause}).
     * This constructor is useful for exceptions that are little more than
     * wrappers for other throwables (for example, {@link java.security.PrivilegedActionException}).
     *
     * @param cause the cause (which is saved for later retrieval by the
     *              {@link Throwable#getCause()} method). (A {@code null} value
     *              is permitted, and indicates that the cause is nonexistent or
     *              unknown.)
     */
    public ServiceException(Throwable cause) {
        super(cause);
    }

    /**
     * Constructs a new {@code ServiceException} with the specified detail message,
     * cause, suppression enabled or disabled, and writable stack trace enabled or
     * disabled.
     *
     * @param message            the detail message.
     * @param cause              the cause. (A {@code null} value is permitted,
     *                           and indicates that the cause is nonexistent or
     *                           unknown.)
     * @param enableSuppression  whether or not suppression is enabled or disabled
     * @param writableStackTrace whether or not the stack trace should be
     *                           writable
     */
    public ServiceException(String message, Throwable cause, boolean enableSuppression, boolean writableStackTrace) {
        super(message, cause, enableSuppression, writableStackTrace);
    }
}