import * as Sentry from "@sentry/react";

export const reportError = (error: Error, message?: string) => {
  Sentry.captureException(error, {
    extra: {
      message,
    },
  });
};