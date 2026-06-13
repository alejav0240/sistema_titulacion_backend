from django.urls import path

from apps.relationships.views import (
    TutorTribunalDetailView,
    TutorTribunalListCreateView,
)

urlpatterns = [
    path('relationships/', TutorTribunalListCreateView.as_view(), name='relationships'),
    path('relationships/<int:pk>/', TutorTribunalDetailView.as_view(), name='relationship_detail'),
]
