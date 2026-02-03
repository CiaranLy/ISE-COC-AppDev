import { useState, useEffect, useCallback, useMemo, ChangeEvent } from 'react';
import GraphCard from './GraphCard';
import { fetchGraphs, checkHealth } from '../services/api';
import { Graph, CollectorGroup } from '../types';

/**
 * Dashboard Component
 * 
 * Automatically fetches and displays all graphs from the database.
 * New graphs are displayed automatically without recompilation -
 * just add data to the database and it will appear on the next refresh.
 * 
 * Features:
 * - Auto-refresh at configurable intervals
 * - Manual refresh button
 * - Connection status indicator
 * - Groups graphs by collector
 */
function Dashboard() {
    const [graphs, setGraphs] = useState<Graph[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
    const [isConnected, setIsConnected] = useState(true);
    const [refreshInterval, setRefreshInterval] = useState(5); // seconds

    // Fetch graphs from the API
    const loadGraphs = useCallback(async () => {
        try {
            const data = await fetchGraphs();
            setGraphs(data);
            setLastUpdated(new Date());
            setIsConnected(true);
            setError(null);
        } catch (err) {
            console.error('Failed to fetch graphs:', err);
            setError(err instanceof Error ? err.message : 'Unknown error');
            setIsConnected(false);
        } finally {
            setLoading(false);
        }
    }, []);

    // Initial load
    useEffect(() => {
        loadGraphs();
    }, [loadGraphs]);

    // Auto-refresh interval
    useEffect(() => {
        if (refreshInterval > 0) {
            const interval = setInterval(() => {
                loadGraphs();
            }, refreshInterval * 1000);
            
            return () => clearInterval(interval);
        }
    }, [refreshInterval, loadGraphs]);

    // Check connection health periodically
    useEffect(() => {
        const healthCheck = setInterval(async () => {
            const healthy = await checkHealth();
            setIsConnected(healthy);
        }, 10000);
        
        return () => clearInterval(healthCheck);
    }, []);

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

    const handleRefreshIntervalChange = (e: ChangeEvent<HTMLSelectElement>) => {
        const value = parseInt(e.target.value, 10);
        setRefreshInterval(value);
    };

    return (
        <div className="dashboard">
            <header className="dashboard-header">
                <div className="header-left">
                    <h1 className="dashboard-title">System Monitor</h1>
                    <p className="dashboard-subtitle">Real-time metrics dashboard</p>
                </div>
                <div className="header-right">
                    <div className="connection-status">
                        <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}></span>
                        <span className="status-text">{isConnected ? 'Connected' : 'Disconnected'}</span>
                    </div>
                    <div className="refresh-controls">
                        <label htmlFor="refresh-interval">Refresh:</label>
                        <select 
                            id="refresh-interval" 
                            value={refreshInterval} 
                            onChange={handleRefreshIntervalChange}
                            className="refresh-select"
                        >
                            <option value={0}>Manual</option>
                            <option value={1}>1s</option>
                            <option value={2}>2s</option>
                            <option value={5}>5s</option>
                            <option value={10}>10s</option>
                            <option value={30}>30s</option>
                            <option value={60}>1m</option>
                        </select>
                        <button onClick={loadGraphs} className="refresh-button" disabled={loading}>
                            {loading ? '⟳' : '↻'} Refresh
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
                    <span>Error: {error}</span>
                </div>
            )}

            <main className="dashboard-content">
                {loading && graphs.length === 0 ? (
                    <div className="loading-container">
                        <div className="loading-spinner"></div>
                        <p>Loading graphs...</p>
                    </div>
                ) : graphs.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-icon">📊</div>
                        <h2>No Graphs Available</h2>
                        <p>Start sending data to the aggregator endpoint to see graphs here.</p>
                        <p className="empty-hint">
                            New graphs will appear automatically - no need to refresh the page!
                        </p>
                    </div>
                ) : (
                    <div className="collectors-container">
                        {groupedGraphs.map((group) => (
                            <section key={group.collector_id} className="collector-section">
                                <h2 className="collector-title">
                                    <span className="collector-icon">📡</span>
                                    {group.collector_name}
                                </h2>
                                <div className="graphs-grid">
                                    {group.graphs.map((graph) => (
                                        <GraphCard key={graph.id} graph={graph} />
                                    ))}
                                </div>
                            </section>
                        ))}
                    </div>
                )}
            </main>

            <footer className="dashboard-footer">
                <p>ISE-COC System Monitor • Graphs update dynamically from database</p>
            </footer>
        </div>
    );
}

export default Dashboard;
