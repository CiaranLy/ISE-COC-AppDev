# Data Model

## Database Tables

The system uses three interconnected tables:

### 1. Collectors Table
```
+------------------+---------------------+---------------------+
|        id        |    display_name     |    time_created     |
+------------------+---------------------+---------------------+
|  INT (PK)        |  VARCHAR(255)       |  DATETIME           |
+------------------+---------------------+---------------------+
```

**Purpose:** Tracks data sources (devices/systems being monitored)
- `id` - Auto-incrementing primary key
- `display_name` - Unique identifier for the collector
- `time_created` - Timestamp when collector was first registered

### 2. Graphs Table
```
+------------------+---------------------+---------------------+
|        id        |        name         |        unit         |
+------------------+---------------------+---------------------+
|  INT (PK)        |  VARCHAR(255)       |  VARCHAR(50)        |
+------------------+---------------------+---------------------+
```

**Purpose:** Defines types of metrics that can be collected
- `id` - Auto-incrementing primary key
- `name` - Unique name for the graph/metric type
- `unit` - Unit of measurement (e.g., "celsius", "percent", "watts")

### 3. Data Table
```
+------------------+---------------------+---------------------+---------------------+---------------------+
|        id        |    collector_id     |      graph_id       |    timestamp_utc    |       content       |
+------------------+---------------------+---------------------+---------------------+---------------------+
|  INT (PK)        |  INT (FK)           |  INT (FK)           |  DATETIME           |  FLOAT              |
+------------------+---------------------+---------------------+---------------------+---------------------+
```

**Purpose:** Stores actual time-series data points
- `id` - Auto-incrementing primary key
- `collector_id` - Foreign key to collectors table
- `graph_id` - Foreign key to graphs table
- `timestamp_utc` - When the data was collected
- `content` - The actual metric value

## Relationships

```
Collectors (1) ─────┐
                    │
                    ├──> (Many) Data
                    │
Graphs (1) ─────────┘
```

- One collector can have many data points
- One graph can be used by many data points (across different collectors)
- Each data point belongs to one collector and one graph

## Aggregator Process Flow

### Step 1: Data Ingestion via /aggregator Endpoint
Client submits JSON payload:
```json
{
  "collector_name": "temp_sensor_01",
  "content": 23.5,
  "unit": "celsius",
  "timestamp": "2026-01-27T14:30:00"  // optional
}
```

### Step 2: Server Processing
1. **Find or Create Collector:**
   - Search collectors table for `display_name = "temp_sensor_01"`
   - If not found, create new collector entry
   - Return `collector_id`

2. **Find or Create Graph:**
   - Search graphs table for `name = "temp_sensor_01"`
   - If not found, create new graph entry with provided unit
   - Return `graph_id`

3. **Create Data Entry:**
   - Insert into data table:
     - `collector_id` (from step 1)
     - `graph_id` (from step 2)
     - `content` (from request)
     - `timestamp_utc` (from request or auto-generated)
   - Return `data_id`

### Step 3: Response
Server returns confirmation:
```json
{
  "success": true,
  "collector_id": 1,
  "graph_id": 1,
  "data_id": 1,
  "message": "Data ingested successfully"
}
```

## Data Retrieval Flow

### GET /graphs
Returns all available graphs:
```json
[
  {
    "id": 1,
    "name": "temp_sensor_01",
    "unit": "celsius"
  },
  {
    "id": 2,
    "name": "humidity_sensor",
    "unit": "percent"
  }
]
```

Server:
1. Queries graphs table
2. Returns all entries with id, name, and unit

## Implementation Notes

- **Single Table for Data:** All time-series data lives in one `data` table for simplicity
- **Automatic Resource Creation:** Collectors and graphs are created on-demand when first referenced
- **Cascade Deletes:** Deleting a collector or graph automatically removes associated data points
- **Indexed Timestamps:** The `timestamp_utc` column is indexed for efficient time-based queries
- **Flexible Schema:** The system can handle any collector name and unit type dynamically

## Future Enhancements (if needed)
- Dynamic table creation per collector for improved query performance at scale
- Additional metadata fields (location, description, tags)
- Data aggregation/rollup tables for historical summaries
- Batch ingestion endpoint for multiple data points at once
