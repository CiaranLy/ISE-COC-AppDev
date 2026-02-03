/**
 * Type definitions for the ISE-COC System Monitor
 */

/** Individual data point from a collector */
export interface DataPoint {
    id: number;
    content: number;
    timestamp_utc: string;
    collector_id: number;
}

/** Graph with associated data points */
export interface Graph {
    id: number;
    collector_id: number;
    collector_name: string;
    unit: string;
    data_points: DataPoint[];
}

/** Grouped graphs by collector */
export interface CollectorGroup {
    collector_name: string;
    collector_id: number;
    graphs: Graph[];
}

/** Chart data point for recharts */
export interface ChartDataPoint {
    timestamp: string;
    fullTimestamp: string;
    value: number;
}

/** Health check response */
export interface HealthResponse {
    status: string;
}
