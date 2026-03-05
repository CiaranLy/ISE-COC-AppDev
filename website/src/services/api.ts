/**
 * API Service for fetching data from the backend.
 *
 * Includes retry logic with exponential backoff, request timeouts,
 * and structured error handling for common HTTP status codes.
 */

import { Graph, HealthResponse } from '../types';
import { API_BASE_URL, HEALTH_CHECK_URL, FETCH_TIMEOUT_MS, FETCH_MAX_RETRIES } from '../config';
import createLogger from './logger';

export { API_BASE_URL } from '../config';

const logger = createLogger('api');

const NON_RETRYABLE_STATUSES = new Set([400, 401, 403, 404, 422]);

function isNonRetryable(status: number): boolean {
    return NON_RETRYABLE_STATUSES.has(status);
}

function backoffDelay(attempt: number): number {
    return Math.min(1000 * 2 ** attempt, 8000);
}

function sleep(ms: number): Promise<void> {
    return new Promise(r => setTimeout(r, ms));
}

async function attemptFetch(url: string, options: RequestInit): Promise<Response> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
    try {
        return await fetch(url, { ...options, signal: controller.signal });
    } finally {
        clearTimeout(timeout);
    }
}

function normalizeError(err: unknown): Error {
    if (err instanceof Error) {
        if (err.name === 'AbortError') return new Error('Request timed out');
        return err;
    }
    return new Error(String(err));
}

function handleResponse(response: Response): Response {
    if (response.ok) return response;

    const msg = `${response.status} ${response.statusText}`;
    if (isNonRetryable(response.status)) throw new Error(msg);
    throw Object.assign(new Error(msg), { retryable: true });
}

async function fetchWithRetry(
    url: string,
    options: RequestInit = {},
    retries: number = FETCH_MAX_RETRIES,
): Promise<Response> {
    let lastError: Error = new Error('Request failed');

    for (let attempt = 0; attempt <= retries; attempt++) {
        try {
            const response = await attemptFetch(url, options);
            return handleResponse(response);
        } catch (err) {
            lastError = normalizeError(err);
            if (isNonRetryable(Number(lastError.message.split(' ')[0]))) throw lastError;
        }

        if (attempt < retries) {
            const delay = backoffDelay(attempt);
            logger.warn('Retry %d/%d for %s in %dms', attempt + 1, retries, url, delay);
            await sleep(delay);
        }
    }

    throw lastError;
}

/**
 * Fetch all graphs with their data points from the backend.
 */
export async function fetchGraphs(): Promise<Graph[]> {
    const response = await fetchWithRetry(`${API_BASE_URL}/graphs`);
    return response.json();
}

/**
 * Check the health status of the backend API.
 */
export async function checkHealth(): Promise<boolean> {
    try {
        const response = await fetchWithRetry(`${HEALTH_CHECK_URL}`, {}, 0);
        const data: HealthResponse = await response.json();
        return data.status === 'ok';
    } catch {
        return false;
    }
}
