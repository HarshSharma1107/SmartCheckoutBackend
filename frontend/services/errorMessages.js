// =============================================================
// SmartCheckout — User-facing error copy
// Maps an ApiError's HTTP status to short, non-technical text a retail
// customer/store employee can act on. Anything with a status-specific
// meaning gets fixed copy here; everything else (400/404/409/422) falls
// through to err.message, which is always backend-authored friendly text
// by the time it reaches here (see backend/main.py's format_validation_errors
// and the {code,message} envelope every router uses).
// =============================================================

export function getDisplayMessage(err) {
  const status = err?.status;
  switch (status) {
    case 0:
      return "No internet connection. Please check your connection and try again.";
    case 401:
      return "Your session has expired. Please contact the store administrator.";
    case 403:
      return "You don't have access to do that. Please contact the store administrator.";
    case 429:
      return "Too many requests. Please wait a moment and try again.";
    default:
      if (typeof status === "number" && status >= 500) {
        return "Something went wrong. Please try again.";
      }
      return err?.message || "Something went wrong. Please try again.";
  }
}
