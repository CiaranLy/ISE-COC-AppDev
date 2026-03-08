import { Graph } from '../types';
import { API_BASE_URL } from '../config';

/**
 * Fetch all graphs with their data points from the backend.
 */
export async function fetchGraphs(): Promise<Graph[]> {
    const response = await fetch(`${API_BASE_URL}/graphs`);

    if (!response.ok) {
        throw new Error(`Failed to fetch graphs: ${response.status} ${response.statusText}`);
    }

    return response.json();
}
