import { useMemo } from 'react';
import {
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Area,
    AreaChart,
} from 'recharts';
import { Graph, ChartDataPoint } from '../types';

interface GraphCardProps {
    graph: Graph;
}

interface CustomTooltipProps {
    active?: boolean;
    payload?: Array<{
        value?: number;
        payload?: ChartDataPoint;
    }>;
}

/**
 * GraphCard Component
 * 
 * Renders a single graph with its data points.
 * New graphs are automatically displayed when added to the database -
 * no recompilation required.
 */
function GraphCard({ graph }: GraphCardProps) {
    // Transform data points for recharts
    const chartData = useMemo((): ChartDataPoint[] => {
        if (!graph.data_points || graph.data_points.length === 0) {
            return [];
        }

        // Sort by timestamp and format for chart
        return graph.data_points
            .slice() // Create a copy to avoid mutating original
            .sort((a, b) => new Date(a.timestamp_utc).getTime() - new Date(b.timestamp_utc).getTime())
            .map((point) => ({
                timestamp: new Date(point.timestamp_utc).toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                }),
                fullTimestamp: new Date(point.timestamp_utc).toLocaleString(),
                value: point.content,
            }));
    }, [graph.data_points]);

    // Get the latest value for display
    const latestValue = chartData.length > 0 ? chartData[chartData.length - 1].value : null;

    // Determine chart color based on unit type
    const getChartColor = (unit: string): string => {
        const unitLower = unit.toLowerCase();
        if (unitLower.includes('cpu')) return '#3b82f6'; // Blue
        if (unitLower.includes('memory') || unitLower.includes('ram')) return '#8b5cf6'; // Purple
        if (unitLower.includes('disk')) return '#f59e0b'; // Orange
        if (unitLower.includes('temp') || unitLower.includes('celsius')) return '#ef4444'; // Red
        if (unitLower.includes('percent')) return '#10b981'; // Green
        return '#6366f1'; // Indigo default
    };

    const chartColor = getChartColor(graph.unit);

    // Format unit display
    const formatUnit = (unit: string): string => {
        const unitMap: Record<string, string> = {
            'cpu_percent': 'CPU %',
            'memory_percent': 'Memory %',
            'memory_mb': 'Memory MB',
            'disk_percent': 'Disk %',
            'celsius': '°C',
            'percent': '%',
        };
        return unitMap[unit.toLowerCase()] || unit;
    };

    const CustomTooltip = ({ active, payload }: CustomTooltipProps) => {
        if (active && payload && payload.length && payload[0].payload) {
            const data = payload[0].payload;
            return (
                <div className="graph-tooltip">
                    <p className="tooltip-time">{data.fullTimestamp}</p>
                    <p className="tooltip-value">
                        <span style={{ color: chartColor }}>{payload[0].value?.toFixed(2)}</span>
                        {' '}{formatUnit(graph.unit)}
                    </p>
                </div>
            );
        }
        return null;
    };

    return (
        <div className="graph-card">
            <div className="graph-header">
                <div className="graph-title-section">
                    <h3 className="graph-title">{graph.collector_name}</h3>
                    <span className="graph-unit">{formatUnit(graph.unit)}</span>
                </div>
                {latestValue !== null && (
                    <div className="graph-current-value" style={{ color: chartColor }}>
                        {latestValue.toFixed(2)}
                    </div>
                )}
            </div>
            
            <div className="graph-chart-container">
                {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={200}>
                        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                            <defs>
                                <linearGradient id={`gradient-${graph.id}`} x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor={chartColor} stopOpacity={0.3} />
                                    <stop offset="95%" stopColor={chartColor} stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis 
                                dataKey="timestamp" 
                                stroke="#9ca3af"
                                fontSize={11}
                                tickLine={false}
                            />
                            <YAxis 
                                stroke="#9ca3af"
                                fontSize={11}
                                tickLine={false}
                                axisLine={false}
                            />
                            <Tooltip content={<CustomTooltip />} />
                            <Area
                                type="monotone"
                                dataKey="value"
                                stroke={chartColor}
                                strokeWidth={2}
                                fill={`url(#gradient-${graph.id})`}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                ) : (
                    <div className="graph-no-data">
                        <p>No data points available</p>
                    </div>
                )}
            </div>
            
            <div className="graph-footer">
                <span className="graph-data-count">
                    {chartData.length} data point{chartData.length !== 1 ? 's' : ''}
                </span>
            </div>
        </div>
    );
}

export default GraphCard;
