import heapq


def build_adjacency_list(edges):
    graph = {}
    for edge in edges:
        graph.setdefault(edge.source.name, []).append(
            (edge.destination.name, edge.latency)
        )
        graph.setdefault(edge.destination.name, [])
    return graph


def shortest_path(graph, source, destination):
    """Return (total_latency, path) using Dijkstra, or None if unreachable."""
    if source == destination:
        return 0.0, [source]

    distances = {source: 0.0}
    previous = {}
    heap = [(0.0, source)]

    while heap:
        current_distance, node = heapq.heappop(heap)
        if current_distance > distances.get(node, float("inf")):
            continue
        if node == destination:
            break
        for neighbor, weight in graph.get(node, []):
            candidate = current_distance + weight
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                previous[neighbor] = node
                heapq.heappush(heap, (candidate, neighbor))

    if destination not in distances:
        return None

    path = [destination]
    current = destination
    while current != source:
        current = previous[current]
        path.append(current)
    path.reverse()
    return distances[destination], path
