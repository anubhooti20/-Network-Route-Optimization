from rest_framework import serializers

from network.models import Edge, Node, RouteQuery


class NodeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        error_messages={
            "required": "Name is required",
            "blank": "Name is required",
            "null": "Name is required",
        }
    )

    class Meta:
        model = Node
        fields = ["id", "name"]
        extra_kwargs = {"name": {"validators": []}}

    def validate_name(self, value):
        name = value.strip() if isinstance(value, str) else value
        if not name:
            raise serializers.ValidationError("Name is required")
        if Node.objects.filter(name=name).exists():
            raise serializers.ValidationError("Node with this name already exists")
        return name


class EdgeReadSerializer(serializers.ModelSerializer):
    source = serializers.CharField(source="source.name")
    destination = serializers.CharField(source="destination.name")

    class Meta:
        model = Edge
        fields = ["id", "source", "destination", "latency"]


class EdgeCreateSerializer(serializers.Serializer):
    source = serializers.CharField(
        error_messages={"required": "Source is required", "blank": "Source is required"}
    )
    destination = serializers.CharField(
        error_messages={
            "required": "Destination is required",
            "blank": "Destination is required",
        }
    )
    latency = serializers.FloatField(
        error_messages={"required": "Latency is required"}
    )

    def validate_source(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Source is required")
        return name

    def validate_destination(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Destination is required")
        return name

    def validate_latency(self, value):
        if value <= 0:
            raise serializers.ValidationError("Latency must be greater than 0")
        return value

    def validate(self, attrs):
        if attrs["source"] == attrs["destination"]:
            raise serializers.ValidationError(
                "Source and destination cannot be the same"
            )
        return attrs


class ShortestRouteSerializer(serializers.Serializer):
    source = serializers.CharField(
        error_messages={"required": "Source is required", "blank": "Source is required"}
    )
    destination = serializers.CharField(
        error_messages={
            "required": "Destination is required",
            "blank": "Destination is required",
        }
    )

    def validate_source(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Source is required")
        return name

    def validate_destination(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Destination is required")
        return name


class RouteQuerySerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ")

    class Meta:
        model = RouteQuery
        fields = ["id", "source", "destination", "total_latency", "path", "created_at"]
