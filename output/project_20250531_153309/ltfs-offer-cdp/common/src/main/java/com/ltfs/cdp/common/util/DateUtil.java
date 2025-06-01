package com.ltfs.cdp.common.util;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.temporal.ChronoUnit;
import java.util.Objects;

/**
 * Utility class for common date and time manipulation operations.
 * This class leverages the {@code java.time} package (Java 8 Date and Time API)
 * for modern, thread-safe, and immutable date/time handling.
 */
public final class DateUtil {

    // Private constructor to prevent instantiation of this utility class.
    private DateUtil() {
        // SonarLint: Utility classes should not have public constructors
    }

    /**
     * Standard date format string: "yyyy-MM-dd" (e.g., 2023-10-26).
     */
    public static final String DATE_FORMAT_YYYY_MM_DD_STR = "yyyy-MM-dd";
    /**
     * {@link DateTimeFormatter} for "yyyy-MM-dd".
     */
    public static final DateTimeFormatter DATE_FORMATTER_YYYY_MM_DD = DateTimeFormatter.ofPattern(DATE_FORMAT_YYYY_MM_DD_STR);

    /**
     * Standard date-time format string: "yyyy-MM-dd HH:mm:ss" (e.g., 2023-10-26 15:30:00).
     */
    public static final String DATETIME_FORMAT_YYYY_MM_DD_HH_MM_SS_STR = "yyyy-MM-dd HH:mm:ss";
    /**
     * {@link DateTimeFormatter} for "yyyy-MM-dd HH:mm:ss".
     */
    public static final DateTimeFormatter DATETIME_FORMATTER_YYYY_MM_DD_HH_MM_SS = DateTimeFormatter.ofPattern(DATETIME_FORMAT_YYYY_MM_DD_HH_MM_SS_STR);

    /**
     * Standard date-time format string with milliseconds: "yyyy-MM-dd HH:mm:ss.SSS" (e.g., 2023-10-26 15:30:00.123).
     */
    public static final String DATETIME_FORMAT_YYYY_MM_DD_HH_MM_SS_SSS_STR = "yyyy-MM-dd HH:mm:ss.SSS";
    /**
     * {@link DateTimeFormatter} for "yyyy-MM-dd HH:mm:ss.SSS".
     */
    public static final DateTimeFormatter DATETIME_FORMATTER_YYYY_MM_DD_HH_MM_SS_SSS = DateTimeFormatter.ofPattern(DATETIME_FORMAT_YYYY_MM_DD_HH_MM_SS_SSS_STR);

    /**
     * Common display date format string: "dd-MM-yyyy" (e.g., 26-10-2023).
     */
    public static final String DATE_FORMAT_DD_MM_YYYY_STR = "dd-MM-yyyy";
    /**
     * {@link DateTimeFormatter} for "dd-MM-yyyy".
     */
    public static final DateTimeFormatter DATE_FORMATTER_DD_MM_YYYY = DateTimeFormatter.ofPattern(DATE_FORMAT_DD_MM_YYYY_STR);

    /**
     * Common display date-time format string: "dd-MM-yyyy HH:mm:ss" (e.g., 26-10-2023 15:30:00).
     */
    public static final String DATETIME_FORMAT_DD_MM_YYYY_HH_MM_SS_STR = "dd-MM-yyyy HH:mm:ss";
    /**
     * {@link DateTimeFormatter} for "dd-MM-yyyy HH:mm:ss".
     */
    public static final DateTimeFormatter DATETIME_FORMATTER_DD_MM_YYYY_HH_MM_SS = DateTimeFormatter.ofPattern(DATETIME_FORMAT_DD_MM_YYYY_HH_MM_SS_STR);

    /**
     * Default system zone ID. This is used for conversions between {@code java.time} and {@code java.util.Date}
     * and for epoch conversions, ensuring consistency with the server's local time zone.
     */
    private static final ZoneId DEFAULT_ZONE_ID = ZoneId.systemDefault();

    /**
     * Returns the current local date and time.
     *
     * @return The current {@link LocalDateTime}.
     */
    public static LocalDateTime getCurrentLocalDateTime() {
        return LocalDateTime.now();
    }

    /**
     * Returns the current local date.
     *
     * @return The current {@link LocalDate}.
     */
    public static LocalDate getCurrentLocalDate() {
        return LocalDate.now();
    }

    /**
     * Formats a {@link LocalDateTime} object into a string using the specified {@link DateTimeFormatter}.
     *
     * @param dateTime  The {@link LocalDateTime} object to format.
     * @param formatter The {@link DateTimeFormatter} to use for formatting.
     * @return The formatted date/time string, or {@code null} if the input {@code dateTime} is {@code null}.
     * @throws NullPointerException If the {@code formatter} is {@code null}.
     */
    public static String format(LocalDateTime dateTime, DateTimeFormatter formatter) {
        if (dateTime == null) {
            return null;
        }
        Objects.requireNonNull(formatter, "Formatter cannot be null");
        return dateTime.format(formatter);
    }

    /**
     * Formats a {@link LocalDateTime} object into a string using the specified pattern string.
     *
     * @param dateTime The {@link LocalDateTime} object to format.
     * @param pattern  The date/time pattern string (e.g., "yyyy-MM-dd HH:mm:ss").
     * @return The formatted date/time string, or {@code null} if the input {@code dateTime} is {@code null}.
     * @throws IllegalArgumentException If the pattern is invalid.
     * @throws NullPointerException If the {@code pattern} is {@code null}.
     */
    public static String format(LocalDateTime dateTime, String pattern) {
        if (dateTime == null) {
            return null;
        }
        Objects.requireNonNull(pattern, "Pattern cannot be null");
        try {
            DateTimeFormatter formatter = DateTimeFormatter.ofPattern(pattern);
            return dateTime.format(formatter);
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("Invalid date/time pattern: " + pattern, e);
        }
    }

    /**
     * Formats a {@link LocalDate} object into a string using the specified {@link DateTimeFormatter}.
     *
     * @param date      The {@link LocalDate} object to format.
     * @param formatter The {@link DateTimeFormatter} to use for formatting.
     * @return The formatted date string, or {@code null} if the input {@code date} is {@code null}.
     * @throws NullPointerException If the {@code formatter} is {@code null}.
     */
    public static String format(LocalDate date, DateTimeFormatter formatter) {
        if (date == null) {
            return null;
        }
        Objects.requireNonNull(formatter, "Formatter cannot be null");
        return date.format(formatter);
    }

    /**
     * Formats a {@link LocalDate} object into a string using the specified pattern string.
     *
     * @param date    The {@link LocalDate} object to format.
     * @param pattern The date pattern string (e.g., "yyyy-MM-dd").
     * @return The formatted date string, or {@code null} if the input {@code date} is {@code null}.
     * @throws IllegalArgumentException If the pattern is invalid.
     * @throws NullPointerException If the {@code pattern} is {@code null}.
     */
    public static String format(LocalDate date, String pattern) {
        if (date == null) {
            return null;
        }
        Objects.requireNonNull(pattern, "Pattern cannot be null");
        try {
            DateTimeFormatter formatter = DateTimeFormatter.ofPattern(pattern);
            return date.format(formatter);
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("Invalid date pattern: " + pattern, e);
        }
    }

    /**
     * Parses a date/time string into a {@link LocalDateTime} object using the specified {@link DateTimeFormatter}.
     *
     * @param dateTimeString The date/time string to parse.
     * @param formatter      The {@link DateTimeFormatter} to use for parsing.
     * @return The parsed {@link LocalDateTime} object.
     * @throws IllegalArgumentException If the {@code dateTimeString} is {@code null}/empty,
     *                                  or if the string cannot be parsed according to the formatter.
     * @throws NullPointerException If the {@code formatter} is {@code null}.
     */
    public static LocalDateTime parseLocalDateTime(String dateTimeString, DateTimeFormatter formatter) {
        Objects.requireNonNull(dateTimeString, "Date/time string cannot be null");
        if (dateTimeString.trim().isEmpty()) {
            throw new IllegalArgumentException("Date/time string cannot be empty");
        }
        Objects.requireNonNull(formatter, "Formatter cannot be null");

        try {
            return LocalDateTime.parse(dateTimeString, formatter);
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException("Failed to parse date/time string '" + dateTimeString +
                    "' with formatter. Error: " + e.getMessage(), e);
        }
    }

    /**
     * Parses a date/time string into a {@link LocalDateTime} object using the specified pattern string.
     *
     * @param dateTimeString The date/time string to parse.
     * @param pattern        The date/time pattern string (e.g., "yyyy-MM-dd HH:mm:ss").
     * @return The parsed {@link LocalDateTime} object.
     * @throws IllegalArgumentException If the {@code dateTimeString} is {@code null}/empty, pattern is {@code null}/invalid,
     *                                  or if the string cannot be parsed according to the pattern.
     */
    public static LocalDateTime parseLocalDateTime(String dateTimeString, String pattern) {
        Objects.requireNonNull(dateTimeString, "Date/time string cannot be null");
        if (dateTimeString.trim().isEmpty()) {
            throw new IllegalArgumentException("Date/time string cannot be empty");
        }
        Objects.requireNonNull(pattern, "Pattern cannot be null");

        try {
            DateTimeFormatter formatter = DateTimeFormatter.ofPattern(pattern);
            return LocalDateTime.parse(dateTimeString, formatter);
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException("Failed to parse date/time string '" + dateTimeString +
                    "' with pattern '" + pattern + "'. Error: " + e.getMessage(), e);
        } catch (IllegalArgumentException e) { // Catches invalid pattern
            throw new IllegalArgumentException("Invalid date/time pattern: " + pattern, e);
        }
    }

    /**
     * Parses a date string into a {@link LocalDate} object using the specified {@link DateTimeFormatter}.
     *
     * @param dateString The date string to parse.
     * @param formatter  The {@link DateTimeFormatter} to use for parsing.
     * @return The parsed {@link LocalDate} object.
     * @throws IllegalArgumentException If the {@code dateString} is {@code null}/empty,
     *                                  or if the string cannot be parsed according to the formatter.
     * @throws NullPointerException If the {@code formatter} is {@code null}.
     */
    public static LocalDate parseLocalDate(String dateString, DateTimeFormatter formatter) {
        Objects.requireNonNull(dateString, "Date string cannot be null");
        if (dateString.trim().isEmpty()) {
            throw new IllegalArgumentException("Date string cannot be empty");
        }
        Objects.requireNonNull(formatter, "Formatter cannot be null");

        try {
            return LocalDate.parse(dateString, formatter);
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException("Failed to parse date string '" + dateString +
                    "' with formatter. Error: " + e.getMessage(), e);
        }
    }

    /**
     * Parses a date string into a {@link LocalDate} object using the specified pattern string.
     *
     * @param dateString The date string to parse.
     * @param pattern    The date pattern string (e.g., "yyyy-MM-dd").
     * @return The parsed {@link LocalDate} object.
     * @throws IllegalArgumentException If the {@code dateString} is {@code null}/empty, pattern is {@code null}/invalid,
     *                                  or if the string cannot be parsed according to the pattern.
     */
    public static LocalDate parseLocalDate(String dateString, String pattern) {
        Objects.requireNonNull(dateString, "Date string cannot be null");
        if (dateString.trim().isEmpty()) {
            throw new IllegalArgumentException("Date string cannot be empty");
        }
        Objects.requireNonNull(pattern, "Pattern cannot be null");

        try {
            DateTimeFormatter formatter = DateTimeFormatter.ofPattern(pattern);
            return LocalDate.parse(dateString, formatter);
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException("Failed to parse date string '" + dateString +
                    "' with pattern '" + pattern + "'. Error: " + e.getMessage(), e);
        } catch (IllegalArgumentException e) { // Catches invalid pattern
            throw new IllegalArgumentException("Invalid date pattern: " + pattern, e);
        }
    }

    /**
     * Converts a {@link LocalDateTime} to epoch milliseconds.
     * The conversion uses the {@link #DEFAULT_ZONE_ID}.
     *
     * @param dateTime The {@link LocalDateTime} to convert.
     * @return The epoch milliseconds, or {@code null} if the input {@code dateTime} is {@code null}.
     */
    public static Long toEpochMilli(LocalDateTime dateTime) {
        if (dateTime == null) {
            return null;
        }
        // Convert LocalDateTime to Instant using default system zone, then to epoch milliseconds
        return dateTime.atZone(DEFAULT_ZONE_ID).toInstant().toEpochMilli();
    }

    /**
     * Converts epoch milliseconds to a {@link LocalDateTime}.
     * The conversion uses the {@link #DEFAULT_ZONE_ID}.
     *
     * @param epochMilli The epoch milliseconds to convert.
     * @return The {@link LocalDateTime} object.
     * @throws IllegalArgumentException If {@code epochMilli} is negative.
     */
    public static LocalDateTime ofEpochMilli(long epochMilli) {
        if (epochMilli < 0) {
            throw new IllegalArgumentException("Epoch milliseconds cannot be negative.");
        }
        // Convert epoch milliseconds to Instant, then to LocalDateTime using default system zone
        return LocalDateTime.ofInstant(java.time.Instant.ofEpochMilli(epochMilli), DEFAULT_ZONE_ID);
    }

    /**
     * Checks if the first {@link LocalDateTime} is strictly before the second {@link LocalDateTime}.
     *
     * @param dateTime1 The first {@link LocalDateTime}.
     * @param dateTime2 The second {@link LocalDateTime}.
     * @return {@code true} if {@code dateTime1} is before {@code dateTime2}, {@code false} otherwise.
     * @throws NullPointerException If any of the input dateTimes is {@code null}.
     */
    public static boolean isBefore(LocalDateTime dateTime1, LocalDateTime dateTime2) {
        Objects.requireNonNull(dateTime1, "First LocalDateTime cannot be null");
        Objects.requireNonNull(dateTime2, "Second LocalDateTime cannot be null");
        return dateTime1.isBefore(dateTime2);
    }

    /**
     * Checks if the first {@link LocalDateTime} is strictly after the second {@link LocalDateTime}.
     *
     * @param dateTime1 The first {@link LocalDateTime}.
     * @param dateTime2 The second {@link LocalDateTime}.
     * @return {@code true} if {@code dateTime1} is after {@code dateTime2}, {@code false} otherwise.
     * @throws NullPointerException If any of the input dateTimes is {@code null}.
     */
    public static boolean isAfter(LocalDateTime dateTime1, LocalDateTime dateTime2) {
        Objects.requireNonNull(dateTime1, "First LocalDateTime cannot be null");
        Objects.requireNonNull(dateTime2, "Second LocalDateTime cannot be null");
        return dateTime1.isAfter(dateTime2);
    }

    /**
     * Adds a specified number of days to a {@link LocalDate}.
     *
     * @param date      The original {@link LocalDate}.
     * @param daysToAdd The number of days to add (can be negative to subtract).
     * @return A new {@link LocalDate} with the added days.
     * @throws NullPointerException If the input {@code date} is {@code null}.
     */
    public static LocalDate addDays(LocalDate date, long daysToAdd) {
        Objects.requireNonNull(date, "Date cannot be null");
        return date.plusDays(daysToAdd);
    }

    /**
     * Adds a specified number of months to a {@link LocalDate}.
     *
     * @param date        The original {@link LocalDate}.
     * @param monthsToAdd The number of months to add (can be negative to subtract).
     * @return A new {@link LocalDate} with the added months.
     * @throws NullPointerException If the input {@code date} is {@code null}.
     */
    public static LocalDate addMonths(LocalDate date, long monthsToAdd) {
        Objects.requireNonNull(date, "Date cannot be null");
        return date.plusMonths(monthsToAdd);
    }

    /**
     * Adds a specified number of years to a {@link LocalDate}.
     *
     * @param date       The original {@link LocalDate}.
     * @param yearsToAdd The number of years to add (can be negative to subtract).
     * @return A new {@link LocalDate} with the added years.
     * @throws NullPointerException If the input {@code date} is {@code null}.
     */
    public static LocalDate addYears(LocalDate date, long yearsToAdd) {
        Objects.requireNonNull(date, "Date cannot be null");
        return date.plusYears(yearsToAdd);
    }

    /**
     * Calculates the difference in days between two {@link LocalDate} objects.
     * The result is positive if {@code endDate} is after {@code startDate}, and negative if {@code endDate} is before {@code startDate}.
     *
     * @param startDate The start date.
     * @param endDate   The end date.
     * @return The number of days between the two dates.
     * @throws NullPointerException If any of the input dates is {@code null}.
     */
    public static long getDifferenceInDays(LocalDate startDate, LocalDate endDate) {
        Objects.requireNonNull(startDate, "Start date cannot be null");
        Objects.requireNonNull(endDate, "End date cannot be null");
        return ChronoUnit.DAYS.between(startDate, endDate);
    }

    /**
     * Converts a {@link java.util.Date} object to {@link LocalDateTime}.
     * The conversion uses the {@link #DEFAULT_ZONE_ID}.
     *
     * @param date The {@link java.util.Date} object to convert.
     * @return The converted {@link LocalDateTime}, or {@code null} if the input {@code date} is {@code null}.
     */
    public static LocalDateTime convertToLocalDateTime(java.util.Date date) {
        if (date == null) {
            return null;
        }
        return LocalDateTime.ofInstant(date.toInstant(), DEFAULT_ZONE_ID);
    }

    /**
     * Converts a {@link LocalDateTime} object to {@link java.util.Date}.
     * The conversion uses the {@link #DEFAULT_ZONE_ID}.
     *
     * @param localDateTime The {@link LocalDateTime} object to convert.
     * @return The converted {@link java.util.Date}, or {@code null} if the input {@code localDateTime} is {@code null}.
     */
    public static java.util.Date convertToUtilDate(LocalDateTime localDateTime) {
        if (localDateTime == null) {
            return null;
        }
        return java.util.Date.from(localDateTime.atZone(DEFAULT_ZONE_ID).toInstant());
    }

    /**
     * Converts a {@link java.util.Date} object to {@link LocalDate}.
     * The conversion uses the {@link #DEFAULT_ZONE_ID}.
     *
     * @param date The {@link java.util.Date} object to convert.
     * @return The converted {@link LocalDate}, or {@code null} if the input {@code date} is {@code null}.
     */
    public static LocalDate convertToLocalDate(java.util.Date date) {
        if (date == null) {
            return null;
        }
        return date.toInstant().atZone(DEFAULT_ZONE_ID).toLocalDate();
    }

    /**
     * Converts a {@link LocalDate} object to {@link java.util.Date}.
     * The conversion uses the {@link #DEFAULT_ZONE_ID}.
     *
     * @param localDate The {@link LocalDate} object to convert.
     * @return The converted {@link java.util.Date}, or {@code null} if the input {@code localDate} is {@code null}.
     */
    public static java.util.Date convertToUtilDate(LocalDate localDate) {
        if (localDate == null) {
            return null;
        }
        // LocalDate does not have time, so we convert it to the start of the day in the default zone.
        return java.util.Date.from(localDate.atStartOfDay(DEFAULT_ZONE_ID).toInstant());
    }
}