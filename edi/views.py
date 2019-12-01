from django.shortcuts import render
from django.http import JsonResponse
from django import forms
from music_metadata.edi.file import EdiFile
from django.conf import settings
try:
    # not part of open source yet
    # without it, just basic EDI processing is available
    from music_metadata.cwr2.file import Cwr2File
except:
    raise
from django.views import View
import json


class FileForm(forms.Form):
    file = forms.FileField()


class VisualValidatorView(View):
    def get(self, request):
        form = FileForm()
        return render(request, 'file.html', {
            'title': 'EDI (CWR/CRD) visual validation',
            'form': form})

    def post(self, request, *args, **kwargs):
        form = FileForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['file']
            edi_file = EdiFile(f)
            edi_file.seek(0)
            edi_file.reconfigure(encoding='latin1')
        else:
            edi_file = None
        return render(request, 'file.html', {
            'title': f'EDI (CWR/CRD) visual validation: { edi_file.name }',
            'form': form,
            'edi_file': edi_file
        })


class ToJson(View):
    def get(self, request):
        form = FileForm()
        return render(request, 'file.html', {
            'title': 'EDI to JSON conversion',
            'form': form})

    def post(self, request, *args, **kwargs):
        form = FileForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['file']
            edi_file = Cwr2File(f)
            edi_file.seek(0)
            edi_file.reconfigure(encoding='latin1')
            d = edi_file.to_dict()
            response = JsonResponse(
                d,
                json_dumps_params={'indent': 4},
            )
            response['Content-Disposition'] = f'attachment; filename="{ edi_file.name }.json"'
            return response
        else:
            edi_file = None
        return self.get(request)
