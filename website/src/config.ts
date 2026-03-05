/**
 * Centralized frontend configuration.
 *
 * Reads from REACT_APP_* environment variables at build time,
 * falling back to sensible defaults for local development.
 */

export const API_BASE_URL: string =
    process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

export const HEALTH_CHECK_URL: string =
    process.env.REACT_APP_HEALTH_URL || 'http://localhost:8000/health';

export const DEFAULT_REFRESH_INTERVAL_SECONDS = 5;

export const HEALTH_CHECK_INTERVAL_MS = 10_000;

export const FETCH_TIMEOUT_MS = 10_000;

export const FETCH_MAX_RETRIES = 3;
