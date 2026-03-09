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

/** Curated ping-pong themed color palette */
const CHART_COLORS = [
    '#FF6B00', // vibrant orange (table / ball)
    '#00E676', // neon green (score glow)
    '#448AFF', // electric blue (paddle highlight)
    '#FF4081', // hot pink (power-up)
    '#FFEA00', // bright yellow (rally)
    '#7C4DFF', // purple (tournament)
    '#00BCD4', // cyan (serve arc)
    '#FF3D00', // deep orange (smash)
];

interface GraphCardProps {
    graph: Graph;
    colorIndex: number;
}

interface CustomTooltipProps {
    active?: boolean;
    payload?: Array<{
        value?: number;
        payload?: ChartDataPoint;
    }>;
    unit: string;
    color: string;
}

function CustomTooltip({ active, payload, unit, color }: CustomTooltipProps) {
    if (active && payload?.length && payload[0].payload) {
        const data = payload[0].payload;
        return (
            <div className="graph-tooltip">
                <p className="tooltip-time">{data.fullTimestamp}</p>
                <p className="tooltip-value">
                    <span style={{ color }}>{payload[0].value?.toFixed(2)}</span>
                    {' '}{unit}
                </p>
            </div>
        );
    }
    return null;
}

/**
 * GraphCard — renders a single graph with an area chart.
 * Color is assigned from a curated palette by index.
 */
function GraphCard({ graph, colorIndex }: GraphCardProps) {
    const chartColor = CHART_COLORS[colorIndex % CHART_COLORS.length];

    const chartData = useMemo((): ChartDataPoint[] => {
        if (!graph.data_points?.length) return [];

        return graph.data_points
            .slice()
            .sort((a, b) => a.timestamp - b.timestamp)
            .map((point) => {
                const dateObj = new Date(point.timestamp * 1000);
                return {
                    timestamp: dateObj.toLocaleTimeString('en-US', {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                    }),
                    fullTimestamp: dateObj.toLocaleString(),
                    value: point.value,
                };
            });
    }, [graph.data_points]);

    const latestValue = chartData.length > 0
        ? chartData[chartData.length - 1].value
        : null;

    return (
        <div className="graph-card">
            <div className="graph-header">
                <div className="graph-title-section">
                    <h3 className="graph-title">
                        {graph.collector_name} <span className="graph-title-session">• {graph.session_id}</span>
                    </h3>
                    <span className="graph-unit">{graph.unit}</span>
                </div>
                {(latestValue !== null && latestValue !== undefined) && (
                    <div className="graph-current-value" style={{ color: chartColor }}>
                        {Number(latestValue).toFixed(2)}
                    </div>
                )}
            </div>

            <div className="graph-chart-container">
                {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={220}>
                        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                            <defs>
                                <linearGradient id={`gradient-${graph.id}`} x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor={chartColor} stopOpacity={0.4} />
                                    <stop offset="95%" stopColor={chartColor} stopOpacity={0.02} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                            <XAxis
                                dataKey="timestamp"
                                stroke="rgba(255,255,255,0.3)"
                                fontSize={11}
                                tickLine={false}
                            />
                            <YAxis
                                stroke="rgba(255,255,255,0.3)"
                                fontSize={11}
                                tickLine={false}
                                axisLine={false}
                            />
                            <Tooltip content={<CustomTooltip unit={graph.unit} color={chartColor} active={false} />} />
                            <Area
                                type="monotone"
                                dataKey="value"
                                stroke={chartColor}
                                strokeWidth={2.5}
                                fill={`url(#gradient-${graph.id})`}
                                dot={false}
                                activeDot={{ r: 5, fill: chartColor, stroke: '#fff', strokeWidth: 2 }}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                ) : (
                    <div className="graph-no-data">
                        <p>🏓 Waiting for data...</p>
                    </div>
                )}
            </div>

            <div className="graph-footer">
                <span className="graph-data-count">
                    {chartData.length} point{chartData.length !== 1 ? 's' : ''} recorded
                </span>
            </div>
        </div>
    );
}

export default GraphCard;
