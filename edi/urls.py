from django.urls import path
from .views import (
    VisualValidatorView, ToJson, SocietyListView, CsvOverview, ExcelOverview)
from django.conf import settings
from django.views.generic import TemplateView


urlpatterns = [
    path('', TemplateView.as_view(template_name="edi.html"),
         {'title': 'EDI - Electronic Data Interchange'},
         name='edi'),
    path('visualvalidator/', VisualValidatorView.as_view(),
         name='visual_validator'),
    path('json/', ToJson.as_view(), name='edi_to_json'),
    path('cwr2/', TemplateView.as_view(template_name="cwr2.html"),
         {'title': 'CWR 2 - Common Works Registration 2.1 and 2.2'},
         name='cwr2'),
    path('cwr3/', TemplateView.as_view(template_name="cwr3.html"),
         {'title': 'CWR 3 - Common Works Registration 3.0 and 3.1'},
         name='cwr3'),
]

if settings.CWR2_AVAILABLE:
    urlpatterns += [
        path('csv/', CsvOverview.as_view(), name='cwr_to_csv'),
        path('excel/', ExcelOverview.as_view(), name='cwr_to_excel'),
        path('societylist/', SocietyListView.as_view(), name='societylist'),
    ]
