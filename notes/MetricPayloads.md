# Metric Payloads

Every metric is sent to the queue (and ultimately to `POST /api/v1/aggregator`) as a JSON object with four fields:

```json
{
    "collector_name": "<string>",
    "content": <float>,
    "unit": "<string>",
    "timestamp": "<ISO 8601 datetime>"
}
```

---

## Desktop Collector (`desktop_pong`)

### Snapshot Metrics (sent each game tick)

**latency_ms** — Round-trip latency in milliseconds.
```json
{
    "collector_name": "desktop_pong",
    "content": 23.5,
    "unit": "latency_ms",
    "timestamp": "2026-03-05T14:30:00+00:00"
}
```

**paddle_y** — Local player's paddle Y position.
```json
{
    "collector_name": "desktop_pong",
    "content": 350.0,
    "unit": "paddle_y",
    "timestamp": "2026-03-05T14:30:00+00:00"
}
```

**collision_count** — Cumulative ball-paddle collisions.
```json
{
    "collector_name": "desktop_pong",
    "content": 7.0,
    "unit": "collision_count",
    "timestamp": "2026-03-05T14:30:00+00:00"
}
```

### Session Start (sent once when a match begins)

**session_start** — Marker value `1.0` indicating a new session.
```json
{
    "collector_name": "desktop_pong",
    "content": 1.0,
    "unit": "session_start",
    "timestamp": "2026-03-05T14:25:00+00:00"
}
```

### Session End (sent once when a match ends)

**session_duration_ms** — Total session duration in milliseconds.
```json
{
    "collector_name": "desktop_pong",
    "content": 300000.0,
    "unit": "session_duration_ms",
    "timestamp": "2026-03-05T14:30:00+00:00"
}
```

**final_score_player1** — Player 1's final score.
```json
{
    "collector_name": "desktop_pong",
    "content": 5.0,
    "unit": "final_score_player1",
    "timestamp": "2026-03-05T14:30:00+00:00"
}
```

**final_score_player2** — Player 2's final score.
```json
{
    "collector_name": "desktop_pong",
    "content": 3.0,
    "unit": "final_score_player2",
    "timestamp": "2026-03-05T14:30:00+00:00"
}
```

---

## Third-Party Collector (`third_party_pong`)

### Snapshot Metrics (sent each game tick)

**paddle_y_player1** — Player 1's paddle Y position.
```json
{
    "collector_name": "third_party_pong",
    "content": 200.0,
    "unit": "paddle_y_player1",
    "timestamp": "2026-03-05T14:30:00+00:00"
}
```

**paddle_y_player2** — Player 2's paddle Y position.
```json
{
    "collector_name": "third_party_pong",
    "content": 400.0,
    "unit": "paddle_y_player2",
    "timestamp": "2026-03-05T14:30:00+00:00"
}
```

**latency_ms_player1** — Player 1's round-trip latency in milliseconds.
```json
{
    "collector_name": "third_party_pong",
    "content": 15.0,
    "unit": "latency_ms_player1",
    "timestamp": "2026-03-05T14:30:00+00:00"
}
```

**latency_ms_player2** — Player 2's round-trip latency in milliseconds.
```json
{
    "collector_name": "third_party_pong",
    "content": 22.0,
    "unit": "latency_ms_player2",
    "timestamp": "2026-03-05T14:30:00+00:00"
}
```

**collision_count** — Cumulative ball-paddle collisions.
```json
{
    "collector_name": "third_party_pong",
    "content": 12.0,
    "unit": "collision_count",
    "timestamp": "2026-03-05T14:30:00+00:00"
}
```

**score_player1** — Player 1's current score (live, during match).
```json
{
    "collector_name": "third_party_pong",
    "content": 3.0,
    "unit": "score_player1",
    "timestamp": "2026-03-05T14:30:00+00:00"
}
```

**score_player2** — Player 2's current score (live, during match).
```json
{
    "collector_name": "third_party_pong",
    "content": 2.0,
    "unit": "score_player2",
    "timestamp": "2026-03-05T14:30:00+00:00"
}
```

### Session Start (sent once when a match begins)

**session_start** — Marker value `1.0` indicating a new session.
```json
{
    "collector_name": "third_party_pong",
    "content": 1.0,
    "unit": "session_start",
    "timestamp": "2026-03-05T14:25:00+00:00"
}
```

### Session End (sent once when a match ends)

**session_duration_ms** — Total session duration in milliseconds.
```json
{
    "collector_name": "third_party_pong",
    "content": 300000.0,
    "unit": "session_duration_ms",
    "timestamp": "2026-03-05T14:30:00+00:00"
}
```

**final_score_player1** — Player 1's final score.
```json
{
    "collector_name": "third_party_pong",
    "content": 5.0,
    "unit": "final_score_player1",
    "timestamp": "2026-03-05T14:30:00+00:00"
}
```

**final_score_player2** — Player 2's final score.
```json
{
    "collector_name": "third_party_pong",
    "content": 3.0,
    "unit": "final_score_player2",
    "timestamp": "2026-03-05T14:30:00+00:00"
}
```

---

## Mobile Collector (`mobile_pong`)

### Snapshot Metrics (sent per Firebase snapshot document)

**latency_ms** — Round-trip latency in milliseconds.
```json
{
    "collector_name": "mobile_pong",
    "content": 45.0,
    "unit": "latency_ms",
    "timestamp": "2026-03-05T14:30:00+00:00"
}
```

**paddle_y** — Local player's paddle Y position.
```json
{
    "collector_name": "mobile_pong",
    "content": 280.0,
    "unit": "paddle_y",
    "timestamp": "2026-03-05T14:30:00+00:00"
}
```

**collision_count** — Cumulative ball-paddle collisions.
```json
{
    "collector_name": "mobile_pong",
    "content": 4.0,
    "unit": "collision_count",
    "timestamp": "2026-03-05T14:30:00+00:00"
}
```

### Session Start (sent when a new `game_sessions` document appears)

**session_start** — Marker value `1.0` indicating a new session.
```json
{
    "collector_name": "mobile_pong",
    "content": 1.0,
    "unit": "session_start",
    "timestamp": "2026-03-05T14:25:00+00:00"
}
```

### Session End (sent when `endedAt` field appears on the session document)

**session_duration_ms** — Total session duration in milliseconds.
```json
{
    "collector_name": "mobile_pong",
    "content": 180000.0,
    "unit": "session_duration_ms",
    "timestamp": "2026-03-05T14:28:00+00:00"
}
```

**final_score_player1** — Player 1's final score.
```json
{
    "collector_name": "mobile_pong",
    "content": 5.0,
    "unit": "final_score_player1",
    "timestamp": "2026-03-05T14:28:00+00:00"
}
```

**final_score_player2** — Player 2's final score.
```json
{
    "collector_name": "mobile_pong",
    "content": 2.0,
    "unit": "final_score_player2",
    "timestamp": "2026-03-05T14:28:00+00:00"
}
```
