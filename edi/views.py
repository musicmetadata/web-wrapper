from django.shortcuts import render
from django.http import StreamingHttpResponse, HttpResponse
from django import forms
from music_metadata.edi.file import EdiFile
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
try:
    # not part of open source yet
    # without it, just basic EDI processing is available
    from music_metadata.cwr2.file import Cwr2File
except:
    if settings.DEBUG:
        raise
    Cwr2File = EdiFile
from django.views import View
from collections import OrderedDict
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


class ToJsonFileForm(FileForm):
    verbosity = forms.ChoiceField(choices=(
        (0, 'Minimal'),
        (1, 'Standard'),
        (2, 'Extreme'),
    ), initial=1)


class ToJson(View):
    def get(self, request):
        form = ToJsonFileForm()
        return render(request, 'file.html', {
            'title': 'EDI to JSON conversion',
            'form': form})

    @staticmethod
    def to_json(edi_file, verbosity):
        indent = 4 if verbosity else None
        yield '{"work_registrations": [\n'
        errors = []
        for i, group in enumerate(edi_file.get_groups()):
            if i:
                yield ',\n'
            for j, transaction in enumerate(group.get_transactions()):
                if j:
                    yield ',\n'
                try:
                    yield json.dumps(
                        transaction.to_dict(verbosity),
                        cls=DjangoJSONEncoder,
                        indent=indent)
                except Exception as e:
                    yield json.dumps(
                        {
                            'valid': False,
                            'errors': [
                                'Registration not parsable',
                                str(e)
                            ],
                            'raw_data': transaction.lines
                        },
                        indent=indent
                    )
            errors += group.errors
        yield '],\n"file": '
        file_data = OrderedDict()
        file_data['name'] = edi_file.name
        file_data['valid'] = edi_file.valid
        file_data['work_count'] = edi_file.transaction_count
        file_data['line_count'] = edi_file.record_count
        file_data['errors'] = [str(e) for e in (edi_file.file_errors + errors)]
        yield json.dumps(file_data, indent=indent)
        yield '}'

    def post(self, request, *args, **kwargs):
        form = ToJsonFileForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['file']
            edi_file = Cwr2File(f)
            edi_file.seek(0)
            edi_file.reconfigure(encoding='latin1')
            d = self.to_json(edi_file, int(form.cleaned_data['verbosity']))
            if settings.DEBUG:
                response = HttpResponse(d)
            else:
                response = StreamingHttpResponse(d)
            response['Content-Disposition'] = (
                f'attachment; filename="{ edi_file.name }.json"')
            response['Content-Type'] = 'application/json'
            return response
        return self.get(request)
