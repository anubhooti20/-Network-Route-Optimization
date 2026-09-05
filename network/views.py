from datetime import datetime, time, timezone as dt_timezone

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from network.models import Edge, Node, RouteQuery
from network.serializers import (
    EdgeCreateSerializer,
    EdgeReadSerializer,
    NodeSerializer,
    RouteQuerySerializer,
    ShortestRouteSerializer,
)
from network.services.graph import build_adjacency_list, shortest_path


def _parse_iso_datetime(value, *, end_of_day=False):
    parsed = parse_datetime(value)
    if parsed is not None:
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, dt_timezone.utc)
        return parsed

    parsed_date = parse_date(value)
    if parsed_date is None:
        return None

    clock = time.max.replace(microsecond=0) if end_of_day else time.min
    parsed = datetime.combine(parsed_date, clock)
    return timezone.make_aware(parsed, dt_timezone.utc)


class NodeListCreateView(APIView):
    def get(self, request):
        nodes = Node.objects.order_by("id")
        return Response(NodeSerializer(nodes, many=True).data)

    def post(self, request):
        serializer = NodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        node = serializer.save()
        return Response(NodeSerializer(node).data, status=status.HTTP_201_CREATED)


class NodeDestroyView(APIView):
    def delete(self, request, pk):
        try:
            node = Node.objects.get(pk=pk)
        except Node.DoesNotExist as exc:
            raise NotFound({"error": "Node not found"}) from exc
        node.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EdgeListCreateView(APIView):
    def get(self, request):
        edges = Edge.objects.select_related("source", "destination").order_by("id")
        return Response(EdgeReadSerializer(edges, many=True).data)

    def post(self, request):
        serializer = EdgeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            source = Node.objects.get(name=data["source"])
        except Node.DoesNotExist as exc:
            raise ValidationError({"error": "Source node not found"}) from exc

        try:
            destination = Node.objects.get(name=data["destination"])
        except Node.DoesNotExist as exc:
            raise ValidationError({"error": "Destination node not found"}) from exc

        if Edge.objects.filter(source=source, destination=destination).exists():
            raise ValidationError({"error": "An edge between these nodes already exists"})

        edge = Edge.objects.create(
            source=source,
            destination=destination,
            latency=data["latency"],
        )
        return Response(EdgeReadSerializer(edge).data, status=status.HTTP_201_CREATED)


class EdgeDestroyView(APIView):
    def delete(self, request, pk):
        try:
            edge = Edge.objects.get(pk=pk)
        except Edge.DoesNotExist as exc:
            raise NotFound({"error": "Edge not found"}) from exc
        edge.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ShortestRouteView(APIView):
    def post(self, request):
        serializer = ShortestRouteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source_name = serializer.validated_data["source"]
        destination_name = serializer.validated_data["destination"]

        source_exists = Node.objects.filter(name=source_name).exists()
        destination_exists = Node.objects.filter(name=destination_name).exists()
        if not source_exists or not destination_exists:
            raise ValidationError({"error": "Invalid or non-existent nodes"})

        edges = Edge.objects.select_related("source", "destination")
        graph = build_adjacency_list(edges)
        graph.setdefault(source_name, [])
        graph.setdefault(destination_name, [])

        result = shortest_path(graph, source_name, destination_name)
        if result is None:
            return Response(
                {
                    "error": (
                        f"No path exists between {source_name} and {destination_name}"
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        total_latency, path = result
        query = RouteQuery.objects.create(
            source=source_name,
            destination=destination_name,
            total_latency=total_latency,
            path=path,
        )
        return Response(
            {
                "total_latency": query.total_latency,
                "path": query.path,
            },
            status=status.HTTP_200_OK,
        )


class RouteHistoryView(APIView):
    def get(self, request):
        source = request.query_params.get("source")
        destination = request.query_params.get("destination")
        limit_raw = request.query_params.get("limit")
        date_from_raw = request.query_params.get("date_from")
        date_to_raw = request.query_params.get("date_to")

        if limit_raw is None:
            limit = 50
        else:
            try:
                limit = int(limit_raw)
            except (TypeError, ValueError) as exc:
                raise ValidationError({"error": "limit must be a positive integer"}) from exc
            if limit <= 0:
                raise ValidationError({"error": "limit must be a positive integer"})

        queryset = RouteQuery.objects.all()
        if source:
            queryset = queryset.filter(source=source)
        if destination:
            queryset = queryset.filter(destination=destination)

        if date_from_raw:
            date_from = _parse_iso_datetime(date_from_raw)
            if date_from is None:
                raise ValidationError({"error": "date_from must be a valid ISO-8601 date"})
            queryset = queryset.filter(created_at__gte=date_from)

        if date_to_raw:
            date_to = _parse_iso_datetime(date_to_raw, end_of_day=True)
            if date_to is None:
                raise ValidationError({"error": "date_to must be a valid ISO-8601 date"})
            queryset = queryset.filter(created_at__lte=date_to)

        queryset = queryset.order_by("-created_at")[:limit]
        return Response(RouteQuerySerializer(queryset, many=True).data)
