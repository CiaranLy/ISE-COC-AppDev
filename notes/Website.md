# Website - System Monitor Dashboard

A React TypeScript web application that displays real-time metrics from the backend API.

## Key Features

- **Dynamic Graph Loading** - Automatically fetches and displays all graphs from the database
- **No Recompilation Required** - New graphs appear automatically when data is added via `/aggregator`
- **Auto-Refresh** - Configurable refresh intervals (1s, 2s, 5s, 10s, 30s, 1m, or manual)
- **Connection Status** - Visual indicator showing backend connectivity
- **Grouped by Collector** - Graphs organized by their source collector
- **Color-Coded Charts** - Different colors based on metric type:
  - CPU metrics → Blue
  - Memory metrics → Purple
  - Disk metrics → Orange
  - Temperature metrics → Red
  - Percent metrics → Green

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                         Website                                  │
│                                                                  │
│   1. Fetches /graphs from backend API                           │
│   2. Groups graphs by collector_name                            │
│   3. Renders each graph as an AreaChart                         │
│   4. Repeats at configured refresh interval                     │
│                                                                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
                    GET /graphs
                            │
                            ▼
┌───────────────────────────────────────────────────────────────┐
│                      Backend API                               │
│                                                                │
│   Returns array of graphs with data_points:                    │
│   [                                                            │
│     {                                                          │
│       id: 1,                                                   │
│       collector_id: 1,                                         │
│       collector_name: "office_pc",                             │
│       unit: "cpu_percent",                                     │
│       data_points: [                                           │
│         { id: 1, content: 45.2, timestamp_utc: "..." },        │
│         { id: 2, content: 48.1, timestamp_utc: "..." }         │
│       ]                                                        │
│     }                                                          │
│   ]                                                            │
└───────────────────────────────────────────────────────────────┘
```

## Project Structure

```
website/
├── public/
│   ├── favicon.ico
│   ├── index.html
│   ├── manifest.json
│   └── robots.txt
├── src/
│   ├── components/
│   │   ├── Dashboard.tsx    # Main dashboard with auto-refresh
│   │   └── GraphCard.tsx    # Individual graph card with chart
│   ├── services/
│   │   └── api.ts           # API calls to backend
│   ├── types/
│   │   └── index.ts         # TypeScript type definitions
│   ├── App.css              # Styling (dark theme)
│   ├── App.tsx              # Root component
│   ├── index.css
│   └── index.tsx            # Entry point
├── package.json
└── tsconfig.json
```

## Configuration

### API URL

The backend API URL can be configured via environment variable:

```bash
# Default: http://localhost:8000
REACT_APP_API_URL=http://your-backend-url npm start
```

Or create a `.env` file:

```
REACT_APP_API_URL=http://localhost:8000
```

## Running the Website

```bash
cd website

# Development
npm start

# Production build
npm run build
```

The development server runs on `http://localhost:3000` by default.

## Components

### Dashboard (`Dashboard.tsx`)

The main component that:
- Fetches graphs from the API on load and at intervals
- Groups graphs by collector name
- Manages refresh interval state
- Shows connection status and last update time
- Renders loading, empty, and error states

### GraphCard (`GraphCard.tsx`)

Displays a single graph with:
- Collector name and unit label
- Current (latest) value prominently displayed
- Area chart visualization using Recharts
- Custom tooltip showing timestamp and value
- Data point count in footer

### API Service (`api.ts`)

- `fetchGraphs()` - Fetches all graphs with data points
- `checkHealth()` - Checks backend health status

## Type Definitions

```typescript
interface DataPoint {
    id: number;
    content: number;
    timestamp_utc: string;
    collector_id: number;
}

interface Graph {
    id: number;
    collector_id: number;
    collector_name: string;
    unit: string;
    data_points: DataPoint[];
}
```

## Adding New Graphs

No code changes required! Simply send data to the backend:

```bash
curl -X POST http://localhost:8000/aggregator \
  -H "Content-Type: application/json" \
  -d '{
    "collector_name": "new_sensor",
    "content": 42.5,
    "unit": "custom_unit"
  }'
```

The new graph will appear on the dashboard at the next refresh.
