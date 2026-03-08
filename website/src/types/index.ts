/** Individual data point from a collector */
export interface DataPoint {
    id: number;
    content: number;
    timestamp_utc: string;
    collector_id: number;
    session_id: string;
}

/** Graph with associated data points */
export interface Graph {
    id: number;
    collector_id: number;
    collector_name: string;
    unit: string;
    session_id: string;
    data_points: DataPoint[];
}

/** Graphs grouped by collector + session */
export interface CollectorGroup {
    collector_name: string;
    collector_id: number;
    session_id: string;
    graphs: Graph[];
}

/** Chart data point for recharts */
export interface ChartDataPoint {
    timestamp: string;
    fullTimestamp: string;
    value: number;
}
