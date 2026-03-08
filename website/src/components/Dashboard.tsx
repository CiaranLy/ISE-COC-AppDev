import { useState, useEffect, useCallback, useMemo, ChangeEvent } from 'react';
import GraphCard from './GraphCard';
import { fetchGraphs } from '../services/api';
import { Graph, CollectorGroup } from '../types';
import { DEFAULT_REFRESH_INTERVAL_SECONDS } from '../config';

/**
 * Dashboard — main page that fetches and displays all graphs
 * grouped by collector. Auto-refreshes at a configurable interval.
 */
function Dashboard() {
    const [graphs, setGraphs] = useState<Graph[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
    const [refreshInterval, setRefreshInterval] = useState(DEFAULT_REFRESH_INTERVAL_SECONDS);

    const loadGraphs = useCallback(async () => {
        try {
            const data = await fetchGraphs();
            setGraphs(data);
            setLastUpdated(new Date());
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load data');
        } finally {
            setLoading(false);
        }
    }, []);

    // Initial load
    useEffect(() => {
        loadGraphs();
    }, [loadGraphs]);

    // Auto-refresh
    useEffect(() => {
        if (refreshInterval > 0) {
            const interval = setInterval(loadGraphs, refreshInterval * 1000);
            return () => clearInterval(interval);
        }
    }, [refreshInterval, loadGraphs]);

    // Group graphs by collector
    const groupedGraphs = useMemo((): CollectorGroup[] => {
        const groups: Record<string, CollectorGroup> = {};
        graphs.forEach((graph) => {
            const key = graph.collector_name;
            if (!groups[key]) {
                groups[key] = {
                    collector_name: graph.collector_name,
                    collector_id: graph.collector_id,
                    graphs: [],
                };
            }
            groups[key].graphs.push(graph);
        });
        return Object.values(groups);
    }, [graphs]);

    const handleRefreshChange = (e: ChangeEvent<HTMLSelectElement>) => {
        setRefreshInterval(parseInt(e.target.value, 10));
    };

    return (
        <div className="dashboard">
            <header className="dashboard-header">
                <div className="header-left">
                    <div className="header-brand">
                        <span className="brand-ball"></span>
                        <h1 className="dashboard-title">Pong Analytics</h1>
                    </div>
                    <p className="dashboard-subtitle">Real-time game metrics</p>
                </div>
                <div className="header-right">
                    <div className="refresh-controls">
                        <label htmlFor="refresh-interval">Auto-refresh:</label>
                        <select
                            id="refresh-interval"
                            value={refreshInterval}
                            onChange={handleRefreshChange}
                            className="refresh-select"
                        >
                            <option value={0}>Off</option>
                            <option value={2}>2s</option>
                            <option value={5}>5s</option>
                            <option value={10}>10s</option>
                            <option value={30}>30s</option>
                        </select>
                        <button
                            onClick={loadGraphs}
                            className="refresh-button"
                            disabled={loading}
                        >
                            ↻ Refresh
                        </button>
                    </div>
                </div>
            </header>

            {lastUpdated && (
                <div className="last-updated">
                    Last updated: {lastUpdated.toLocaleTimeString()}
                </div>
            )}

            {error && (
                <div className="error-banner">
                    <span className="error-icon">⚠</span>
                    <span>{error}</span>
                </div>
            )}

            <main className="dashboard-content">
                {loading && graphs.length === 0 ? (
                    <div className="loading-container">
                        <div className="pong-loader">
                            <div className="loader-paddle left"></div>
                            <div className="loader-ball"></div>
                            <div className="loader-paddle right"></div>
                        </div>
                        <p>Loading match data...</p>
                    </div>
                ) : graphs.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-icon">🏓</div>
                        <h2>No Match Data Yet</h2>
                        <p>Start a game to see analytics appear here automatically.</p>
                    </div>
                ) : (
                    <div className="collectors-container">
                        {groupedGraphs.map((group) => (
                            <section key={group.collector_id} className="collector-section">
                                <h2 className="collector-title">
                                    <span className="collector-icon">🏓</span>
                                    {group.collector_name}
                                </h2>
                                <div className="net-divider"></div>
                                <div className="graphs-grid">
                                    {group.graphs.map((graph, index) => (
                                        <GraphCard key={graph.id} graph={graph} colorIndex={index} />
                                    ))}
                                </div>
                            </section>
                        ))}
                    </div>
                )}
            </main>

            <footer className="dashboard-footer">
                <p>🏓 Pong Analytics • Game data updates in real-time</p>
            </footer>
        </div>
    );
}

export default Dashboard;
