# Data Model

```
+------------------+------------------+---------------------+------------------+------------------+-----------------+
|        id        |   timestamp_utc  |  data_collector_id  |     graph_id     |    graph_name    |     content     |
+------------------+------------------+---------------------+------------------+------------------+-----------------+
|  INT (PK)        |  DATETIME        |  INT (FK)           |  INT             |  VARCHAR         |  Int            |
+------------------+------------------+---------------------+------------------+------------------+-----------------+
```

Above is the data model, we can leave all data in the single DB table as a prototype, if we have time we can dynamically sort the data to seperate tables later if we find the need.

id -> serverside identifier (not needed in json input)
timestamp_utc -> time of data collection
data_collector_id(coll-id) -> identifier for a specific collector (will need to message server for the latest id (how many collecters present + 1) before sending data to have the system be fully autonomous)
graph_id -> numerical id for a graph for a specific collecter (each collecter will have graph 1)
content -> data to be graphed

## Aggregator Process Flow
1. Server selects all coll-id to find highest numerical value
2. Server iterate through the data collectors and each of their graphs and writes their content to history
3. Server sends json structure of graph data in order of time, with collector and graph ids to the web application
