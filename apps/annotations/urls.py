from django.urls import path

from apps.annotations.views import (
    AnotacionDetailView,
    AprobarView,
    HistorialView,
    ReobservarView,
    SubsanarView,
    VersionAnotacionesView,
)

urlpatterns = [
    path(
        'versions/<int:pk>/annotations/',
        VersionAnotacionesView.as_view(),
        name='version_annotations',
    ),
    path('annotations/<int:pk>/', AnotacionDetailView.as_view(), name='annotation_detail'),
    path('annotations/<int:pk>/subsanar/', SubsanarView.as_view(), name='annotation_subsanar'),
    path('annotations/<int:pk>/aprobar/', AprobarView.as_view(), name='annotation_aprobar'),
    path('annotations/<int:pk>/reobservar/', ReobservarView.as_view(), name='annotation_reobservar'),
    path('annotations/<int:pk>/historial/', HistorialView.as_view(), name='annotation_historial'),
]
