from django.urls import path
from .views import EdiImportView

urlpatterns = [
    path('', EdiImportView.as_view(), name='edi_import'),
]
