import { Graph } from '../types';
import { API_BASE_URL } from '../config';

/**
 * Fetch graphs for a window of sessions with their data points from the backend.
 *
 * Sessions are paginated using `session_offset` (0-based) and `session_limit`.
 */
export async function fetchGraphs(
    sessionOffset = 0,
    sessionLimit = 3,
): Promise<Graph[]> {
    const params = new URLSearchParams({
        session_offset: String(sessionOffset),
        session_limit: String(sessionLimit),
    });
    const response = await fetch(`${API_BASE_URL}/graphs?${params.toString()}`);

    if (!response.ok) {
        let errorMessage = `Failed to fetch graphs: ${response.status} ${response.statusText}`;
        try {
            const errorData = await response.json();
            if (errorData.detail) errorMessage = errorData.detail;
            else if (errorData.error) errorMessage = errorData.error;
        } catch (e) {
            // Ignore JSON parsing errors
        }
        throw new Error(errorMessage);
    }

    return response.json();
}

/**
 * Set or clear the max_value threshold for a graph.
 */
export async function updateThreshold(graphId: number, maxValue: number | null): Promise<void> {
    await fetch(`${API_BASE_URL}/graphs/${graphId}/threshold`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ max_value: maxValue }),
    });
}

/**
 * Create an alert when a live value exceeds a threshold.
 */
export async function createAlert(
    collectorName: string,
    unit: string,
    value: number,
    threshold: number,
): Promise<void> {
    await fetch(`${API_BASE_URL}/alerts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ collector_name: collectorName, unit, value, threshold }),
    });
}
