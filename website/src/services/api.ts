/**
 * API Service for fetching data from the backend.
 * 
 * Configuration can be changed without recompiling by modifying
 * the API_BASE_URL or using environment variables.
 */

import { Graph, HealthResponse } from '../types';

// API base URL - can be configured via environment variable
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/**
 * Fetch all graphs with their data points from the backend.
 * 
 * Returns an array of graph objects, each containing:
 * - id: number
 * - collector_id: number
 * - collector_name: string
 * - unit: string
 * - data_points: Array of { id, content, timestamp_utc, collector_id }
 */
export async function fetchGraphs(): Promise<Graph[]> {
    const response = await fetch(`${API_BASE_URL}/graphs`);
    
    if (!response.ok) {
        throw new Error(`Failed to fetch graphs: ${response.status} ${response.statusText}`);
    }
    
    return response.json();
}

/**
 * Check the health status of the backend API.
 */
export async function checkHealth(): Promise<boolean> {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data: HealthResponse = await response.json();
        return data.status === 'ok';
    } catch {
        return false;
    }
}

export { API_BASE_URL };
