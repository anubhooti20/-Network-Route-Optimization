from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from network.models import Edge, Node, RouteQuery


class NetworkApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _create_node(self, name):
        return self.client.post("/nodes", {"name": name}, format="json")

    def _create_edge(self, source, destination, latency):
        return self.client.post(
            "/edges",
            {"source": source, "destination": destination, "latency": latency},
            format="json",
        )

    def test_create_node_success(self):
        response = self._create_node("ServerA")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "ServerA")
        self.assertIn("id", response.data)

    def test_create_node_missing_name(self):
        response = self.client.post("/nodes", {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_create_node_duplicate_name(self):
        self._create_node("ServerA")
        response = self._create_node("ServerA")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_list_nodes(self):
        self._create_node("ServerA")
        self._create_node("ServerB")
        response = self.client.get("/nodes")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([node["name"] for node in response.data], ["ServerA", "ServerB"])

    def test_delete_node_cascades_edges(self):
        self._create_node("ServerA")
        self._create_node("ServerB")
        self._create_edge("ServerA", "ServerB", 10)
        node_id = Node.objects.get(name="ServerA").id

        response = self.client.delete(f"/nodes/{node_id}")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Node.objects.filter(name="ServerA").exists())
        self.assertEqual(Edge.objects.count(), 0)

    def test_delete_missing_node(self):
        response = self.client.delete("/nodes/999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "Node not found")

    def test_create_edge_success(self):
        self._create_node("ServerA")
        self._create_node("ServerB")
        response = self._create_edge("ServerA", "ServerB", 12.5)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["source"], "ServerA")
        self.assertEqual(response.data["destination"], "ServerB")
        self.assertEqual(response.data["latency"], 12.5)

    def test_create_edge_missing_fields(self):
        response = self.client.post("/edges", {"latency": 1}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_create_edge_nonpositive_latency(self):
        self._create_node("ServerA")
        self._create_node("ServerB")
        response = self._create_edge("ServerA", "ServerB", 0)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_create_edge_missing_nodes(self):
        self._create_node("ServerA")
        response = self._create_edge("ServerA", "ServerB", 5)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Destination node not found")

    def test_create_duplicate_edge(self):
        self._create_node("ServerA")
        self._create_node("ServerB")
        self._create_edge("ServerA", "ServerB", 5)
        response = self._create_edge("ServerA", "ServerB", 8)
        self.assertEqual(response.status_code, 400)
        self.assertIn("already exists", response.data["error"])

    def test_create_self_loop_rejected(self):
        self._create_node("ServerA")
        response = self._create_edge("ServerA", "ServerA", 5)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_directed_edges_are_independent(self):
        self._create_node("ServerA")
        self._create_node("ServerB")
        first = self._create_edge("ServerA", "ServerB", 5)
        second = self._create_edge("ServerB", "ServerA", 9)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)

    def test_list_and_delete_edge(self):
        self._create_node("ServerA")
        self._create_node("ServerB")
        created = self._create_edge("ServerA", "ServerB", 4)
        listed = self.client.get("/edges")
        self.assertEqual(len(listed.data), 1)

        deleted = self.client.delete(f"/edges/{created.data['id']}")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.client.get("/edges").data, [])

    def test_shortest_route_success(self):
        for name in ["ServerA", "ServerB", "ServerD"]:
            self._create_node(name)
        self._create_edge("ServerA", "ServerB", 12.5)
        self._create_edge("ServerB", "ServerD", 10.9)

        response = self.client.post(
            "/routes/shortest",
            {"source": "ServerA", "destination": "ServerD"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["path"], ["ServerA", "ServerB", "ServerD"])
        self.assertAlmostEqual(response.data["total_latency"], 23.4)

    def test_shortest_route_picks_lower_latency(self):
        for name in ["A", "B", "C"]:
            self._create_node(name)
        self._create_edge("A", "B", 10)
        self._create_edge("A", "C", 3)
        self._create_edge("C", "B", 3)

        response = self.client.post(
            "/routes/shortest",
            {"source": "A", "destination": "B"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["path"], ["A", "C", "B"])
        self.assertAlmostEqual(response.data["total_latency"], 6)

    def test_shortest_route_same_node(self):
        self._create_node("ServerA")
        response = self.client.post(
            "/routes/shortest",
            {"source": "ServerA", "destination": "ServerA"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["path"], ["ServerA"])
        self.assertEqual(response.data["total_latency"], 0)

    def test_shortest_route_no_path(self):
        self._create_node("ServerA")
        self._create_node("ServerD")
        response = self.client.post(
            "/routes/shortest",
            {"source": "ServerA", "destination": "ServerD"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["error"], "No path exists between ServerA and ServerD"
        )
        self.assertEqual(RouteQuery.objects.count(), 0)

    def test_shortest_route_invalid_nodes(self):
        self._create_node("ServerA")
        response = self.client.post(
            "/routes/shortest",
            {"source": "ServerA", "destination": "Missing"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Invalid or non-existent nodes")

    def test_history_records_successful_queries_and_filters(self):
        for name in ["ServerA", "ServerB", "ServerC"]:
            self._create_node(name)
        self._create_edge("ServerA", "ServerB", 5)
        self._create_edge("ServerB", "ServerC", 5.1)

        self.client.post(
            "/routes/shortest",
            {"source": "ServerA", "destination": "ServerC"},
            format="json",
        )
        self.client.post(
            "/routes/shortest",
            {"source": "ServerB", "destination": "ServerC"},
            format="json",
        )

        history = self.client.get("/routes/history")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.data), 2)
        self.assertEqual(history.data[0]["source"], "ServerB")
        self.assertIn("created_at", history.data[0])

        filtered = self.client.get("/routes/history", {"source": "ServerA"})
        self.assertEqual(len(filtered.data), 1)
        self.assertEqual(filtered.data[0]["destination"], "ServerC")
        self.assertEqual(filtered.data[0]["path"], ["ServerA", "ServerB", "ServerC"])

        limited = self.client.get("/routes/history", {"limit": 1})
        self.assertEqual(len(limited.data), 1)

    def test_history_invalid_limit(self):
        response = self.client.get("/routes/history", {"limit": "abc"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_history_date_filters(self):
        RouteQuery.objects.create(
            source="ServerA",
            destination="ServerB",
            total_latency=1.0,
            path=["ServerA", "ServerB"],
        )
        old = RouteQuery.objects.get()
        RouteQuery.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=3)
        )

        RouteQuery.objects.create(
            source="ServerA",
            destination="ServerC",
            total_latency=2.0,
            path=["ServerA", "ServerC"],
        )

        today = timezone.now().date().isoformat()
        recent = self.client.get("/routes/history", {"date_from": today})
        self.assertEqual(len(recent.data), 1)
        self.assertEqual(recent.data[0]["destination"], "ServerC")

        invalid = self.client.get("/routes/history", {"date_from": "not-a-date"})
        self.assertEqual(invalid.status_code, 400)
