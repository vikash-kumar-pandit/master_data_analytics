/**
 * Extract readable error message from various error response formats
 * @param {any} error - The error object from axios or fetch
 * @returns {string} - A readable error message
 */
export function getErrorMessage(error) {
  // Handle Pydantic validation errors (array of error objects)
  if (Array.isArray(error)) {
    return error
      .map((err) => {
        if (typeof err === 'string') return err;
        if (err.msg) return err.msg;
        if (err.message) return err.message;
        return JSON.stringify(err);
      })
      .join('; ');
  }

  // Handle single error object
  if (typeof error === 'object' && error !== null) {
    if (error.msg) return error.msg;
    if (error.message) return error.message;
    if (error.detail) return getErrorMessage(error.detail); // Recursive for nested errors
  }

  // Handle string errors
  if (typeof error === 'string') {
    return error;
  }

  return 'An unexpected error occurred. Please try again.';
}

/**
 * Extract error message from axios error response
 * @param {AxiosError} axiosError - The axios error object
 * @param {string} fallbackMessage - Default message if extraction fails
 * @returns {string} - A readable error message
 */
export function getAxiosErrorMessage(axiosError, fallbackMessage = 'Request failed') {
  try {
    // Check for response data detail (Pydantic errors are often here)
    if (axiosError?.response?.data?.detail) {
      return getErrorMessage(axiosError.response.data.detail);
    }

    // Check for response data message
    if (axiosError?.response?.data?.message) {
      return axiosError.response.data.message;
    }

    // Check for response data error
    if (axiosError?.response?.data?.error) {
      return getErrorMessage(axiosError.response.data.error);
    }

    // Check for error message
    if (axiosError?.message) {
      return axiosError.message;
    }

    return fallbackMessage;
  } catch {
    return fallbackMessage;
  }
}

/**
 * Get actionable recovery suggestion based on error state
 * @param {any} error - The axios or native error object
 * @returns {string} - Actionable suggestion string
 */
export function getActionableSuggestion(error) {
  if (error?.message === 'Network Error' || error?.code === 'ERR_NETWORK') {
    return 'Could not connect to the backend server. Please verify Uvicorn is running at http://localhost:8000.';
  }

  const status = error?.response?.status;
  if (status === 401) {
    return 'Your session has expired. Please log in again.';
  }
  if (status === 403) {
    return 'Access denied. You do not have permissions for this resource.';
  }
  if (status === 404) {
    return 'The requested resource was not found on the server.';
  }
  if (status === 413) {
    return 'The file size is too large. Please split it or upload a smaller file.';
  }
  if (status === 422) {
    return 'Data validation failed. Please check that headers and values match required formats.';
  }
  if (status >= 500) {
    return 'Internal server error. Please check backend Celery worker and database logs.';
  }
  return 'Please retry your action, or contact platform support if the problem persists.';
}
