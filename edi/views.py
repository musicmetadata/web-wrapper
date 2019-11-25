from django.shortcuts import render
from django import forms
from music_metadata.edi.file import EdiFile
try:
    # not part of open source yet
    # without it, just basic EDI processing is available
    from music_metadata.cwr2.file import Cwr2File
except:
    pass
from django.views import View


class FileForm(forms.Form):
    file = forms.FileField()


class EdiImportView(View):
    def get(self, request):
        form = FileForm()
        return render(request, 'file.html', {
            'title': 'EDI (CWR/CRD) file conversion',
            'form': form})

    def post(self, request, *args, **kwargs):
        form = FileForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['file']
            edi_file = EdiFile(f)
            edi_file.seek(0)
            edi_file.reconfigure(encoding='latin1')

        return render(request, 'file.html', {
            'title': 'EDI (CWR/CRD) basic parsing and validation',
            'form': form,
            'edi_file': edi_file
        })
