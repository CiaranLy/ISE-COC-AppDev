import { Graph } from '../types';
import { API_BASE_URL } from '../config';

/**
 * Fetch all graphs with their data points from the backend.
 */
export async function fetchGraphs(): Promise<Graph[]> {
    const response = await fetch(`${API_BASE_URL}/graphs`);

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
