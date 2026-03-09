import { useState, useEffect, useCallback, useMemo, ChangeEvent } from 'react';
import GraphCard from './GraphCard';
import { fetchGraphs } from '../services/api';
import { Graph } from '../types';
import { DEFAULT_REFRESH_INTERVAL_SECONDS } from '../config';

/**
 * Dashboard — displays all graphs in a matrix:
 *   columns = collectors, rows = sessions
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

    useEffect(() => { loadGraphs(); }, [loadGraphs]);

    useEffect(() => {
        if (refreshInterval > 0) {
            const interval = setInterval(loadGraphs, refreshInterval * 1000);
            return () => clearInterval(interval);
        }
    }, [refreshInterval, loadGraphs]);

    const [activeCollector, setActiveCollector] = useState<string | null>(null);

    // Unique collectors for tabs
    const collectors = useMemo(() => {
        const seen = new Set<string>();
        const result: { name: string; id: number }[] = [];
        graphs.forEach(g => {
            if (!seen.has(g.collector_name)) {
                seen.add(g.collector_name);
                result.push({ name: g.collector_name, id: g.collector_id });
            }
        });
        return result;
    }, [graphs]);

    useEffect(() => {
        if (collectors.length > 0 && !activeCollector) {
            setActiveCollector(collectors[0].name);
        } else if (collectors.length > 0 && activeCollector && !collectors.find(c => c.name === activeCollector)) {
            setActiveCollector(collectors[0].name);
        }
    }, [collectors, activeCollector]);

    // Active collector's graphs grouped by session
    const sessionsForActive = useMemo(() => {
        const activeGraphs = graphs.filter(g => g.collector_name === activeCollector);
        const sessionMap: Record<string, Graph[]> = {};
        activeGraphs.forEach(g => {
            if (!sessionMap[g.session_id]) sessionMap[g.session_id] = [];
            sessionMap[g.session_id].push(g);
        });
        return sessionMap;
    }, [graphs, activeCollector]);

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
                    <div className="dashboard-tabs-container">
                        <div className="dashboard-tabs">
                            {collectors.map(collector => (
                                <button
                                    key={collector.id}
                                    className={`tab-button ${activeCollector === collector.name ? 'active' : ''}`}
                                    onClick={() => setActiveCollector(collector.name)}
                                >
                                    <span className="collector-icon">🏓</span>
                                    {collector.name}
                                </button>
                            ))}
                        </div>

                        <div className="tab-content">
                            {Object.entries(sessionsForActive).map(([sessionId, sessionGraphs], sIdx) => (
                                <div key={sessionId} className="session-section">
                                    <div className="session-header">
                                        <h2 className="session-title">Session</h2>
                                        <span className="session-id-badge">{sessionId}</span>
                                    </div>
                                    <div className="graphs-grid">
                                        {sessionGraphs.map((graph, i) => (
                                            <GraphCard
                                                key={graph.id}
                                                graph={graph}
                                                // Generate color index deterministically
                                                colorIndex={i}
                                            />
                                        ))}
                                    </div>
                                    {/* Don't show net divider after the last session */}
                                    {sIdx < Object.keys(sessionsForActive).length - 1 && (
                                        <div className="net-divider"></div>
                                    )}
                                </div>
                            ))}
                        </div>
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
