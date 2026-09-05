from django.urls import re_path

from network.views import (
    EdgeDestroyView,
    EdgeListCreateView,
    NodeDestroyView,
    NodeListCreateView,
    RouteHistoryView,
    ShortestRouteView,
)

urlpatterns = [
    re_path(r"^nodes/?$", NodeListCreateView.as_view()),
    re_path(r"^nodes/(?P<pk>\d+)/?$", NodeDestroyView.as_view()),
    re_path(r"^edges/?$", EdgeListCreateView.as_view()),
    re_path(r"^edges/(?P<pk>\d+)/?$", EdgeDestroyView.as_view()),
    re_path(r"^routes/shortest/?$", ShortestRouteView.as_view()),
    re_path(r"^routes/history/?$", RouteHistoryView.as_view()),
]
