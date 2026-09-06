# Network Route Optimization API

Django REST API that models a directed network, finds the lowest-latency path between two servers, and keeps a history of successful route queries.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations network
python manage.py migrate
python manage.py runserver
```

Migration files stay local (they are gitignored). Create them on each machine with `makemigrations` before `migrate`.

The API listens on `http://127.0.0.1:8000`. Paths work with or without a trailing slash.

## Tests

```bash
python manage.py test
```

## Endpoints

### Add node

```bash
curl -X POST http://127.0.0.1:8000/nodes \
  -H "Content-Type: application/json" \
  -d '{"name": "ServerA"}'
```

`201` — `{ "id": 1, "name": "ServerA" }`  
`400` — name missing or duplicate

### Add edge

```bash
curl -X POST http://127.0.0.1:8000/edges \
  -H "Content-Type: application/json" \
  -d '{"source": "ServerA", "destination": "ServerB", "latency": 12.5}'
```

`201` — created edge  
`400` — missing nodes, `latency <= 0`, duplicate pair, or self-loop

### Shortest route

```bash
curl -X POST http://127.0.0.1:8000/routes/shortest \
  -H "Content-Type: application/json" \
  -d '{"source": "ServerA", "destination": "ServerD"}'
```

`200` — `{ "total_latency": 23.4, "path": ["ServerA", "ServerB", "ServerD"] }`  
`404` — no path exists  
`400` — invalid or missing nodes

Successful lookups are stored in history. Failed lookups are not.

### Route history

```bash
curl "http://127.0.0.1:8000/routes/history?source=ServerA&limit=10"
```

Optional query params: `source`, `destination`, `limit` (default 50), `date_from`, `date_to` (ISO-8601).

### Optional helpers

```bash
curl http://127.0.0.1:8000/nodes
curl http://127.0.0.1:8000/edges
curl -X DELETE http://127.0.0.1:8000/nodes/1
curl -X DELETE http://127.0.0.1:8000/edges/1
```

Deleting a node also deletes its incident edges. History rows are kept.

## Sample graph

```bash
curl -X POST http://127.0.0.1:8000/nodes -H "Content-Type: application/json" -d '{"name":"ServerA"}'
curl -X POST http://127.0.0.1:8000/nodes -H "Content-Type: application/json" -d '{"name":"ServerB"}'
curl -X POST http://127.0.0.1:8000/nodes -H "Content-Type: application/json" -d '{"name":"ServerD"}'
curl -X POST http://127.0.0.1:8000/edges -H "Content-Type: application/json" -d '{"source":"ServerA","destination":"ServerB","latency":12.5}'
curl -X POST http://127.0.0.1:8000/edges -H "Content-Type: application/json" -d '{"source":"ServerB","destination":"ServerD","latency":10.9}'
curl -X POST http://127.0.0.1:8000/routes/shortest -H "Content-Type: application/json" -d '{"source":"ServerA","destination":"ServerD"}'
```
