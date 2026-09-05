from django.urls import include, path

urlpatterns = [
    path("", include("network.urls")),
]
