from django.shortcuts import render
from django.http import (
    HttpResponse, StreamingHttpResponse, HttpResponseBadRequest)
from django import forms
from music_metadata.edi.file import EdiFile
from music_metadata.cwr2.fields import SocietyField
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
try:
    # not part of open source yet
    # without it, just basic EDI processing is available
    from music_metadata.cwr2.file import Cwr2File
except:
    if settings.DEBUG:
        raise
from django.views import View
from collections import OrderedDict
import json


class FileForm(forms.Form):
    file = forms.FileField()


class VisualValidatorView(View):
    def get(self, request):
        form = FileForm()
        return render(request, 'file.html', {
            'title': 'Parsing and Visual Validation',
            'form': form})

    def post(self, request, *args, **kwargs):
        form = FileForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['file']
            edi_file = EdiFile(f)
            edi_file.seek(0)
            edi_file.reconfigure(encoding='latin1')
            title = f'Parsing and Visual Validation: { edi_file.name }'
        else:
            edi_file = None
            title = 'Parsing and Visual Validation'
        return render(request, 'file.html', {
            'title': title,
            'form': form,
            'edi_file': edi_file
        })


class ToJsonFileForm(FileForm):
    verbosity = forms.ChoiceField(choices=(
        (0, 'Minimal'),
        (1, 'Standard'),
        (2, 'Extreme'),
    ), initial=1)
    download = forms.BooleanField(initial=False, required=False)


class ToJson(View):

    def get(self, request):
        form = ToJsonFileForm()
        return render(request, 'file.html', {
            'title': 'CWR 2.x to JSON - Conversion with Validation',
            'form': form})

    @staticmethod
    def to_json(edi_file, verbosity):
        indent = 4 if verbosity else None
        yield '{\n\n'
        submitter_data = edi_file.get_header().get_submitter_dict(verbosity)
        yield '"submitter": '
        yield json.dumps(submitter_data, cls=DjangoJSONEncoder, indent=indent)
        yield ',\n\n"work_registrations": [\n'
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
        yield '\n],\n\n"file": '
        file_data = edi_file.get_header().get_transmission_dict()
        file_data['name'] = edi_file.name
        file_data['valid'] = edi_file.valid
        file_data['work_count'] = edi_file.transaction_count
        file_data['line_count'] = edi_file.record_count
        file_data['errors'] = [str(e) for e in (edi_file.file_errors + errors)]
        yield json.dumps(file_data, cls=DjangoJSONEncoder, indent=indent)
        yield '\n\n}'

    def post(self, request, *args, **kwargs):
        form = ToJsonFileForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['file']
            try:
                edi_file = EdiFile(f)
                edi_file.seek(0)
                edi_file.reconfigure(encoding='latin1')
                d = self.to_json(edi_file, int(form.cleaned_data['verbosity']))
            except Exception as e:
                if settings.DEBUG:
                    raise
                return HttpResponseBadRequest('This file can not be processed.')
            if form.cleaned_data['download']:
                if settings.DEBUG:
                    response = HttpResponse(d)
                else:
                    response = StreamingHttpResponse(d)
                response['Content-Disposition'] = (
                    f'attachment; filename="{ edi_file.name }.json"')
                response['Content-Type'] = 'application/json'
                return response
            else:
                return render(request, 'file.html', {
                    'title':
                        'CWR 2.x (EDI) to JSON - Conversion with Validation: '
                        f'{ edi_file.name }',
                    'form': form,
                    'pre': ''.join(d)
                })
        return self.get(request)


class SocietyListView(View):

    def get(self, request):
        form = FileForm()
        return render(request, 'file.html', {
            'title': 'List societies from a CWR file',
            'form': form})

    def process_cwr2(self, edi_file):
        combinations = dict()
        for group in edi_file.get_groups():
            for transaction in group.get_transactions():
                for record in transaction.records:
                    if record.record_type in ['SPU', 'OPU', 'SWR', 'OWR']:
                        if 'pr_affiliation_society_number' in record.errors:
                            record.pr_affiliation_society_number = None
                        if 'mr_affiliation_society_number' in record.errors:
                            record.mr_affiliation_society_number = None
                        if 'sr_affiliation_society_number' in record.errors:
                            record.sr_affiliation_society_number = None
                        d = (
                            record.pr_affiliation_society_number,
                            SocietyField().verbose(
                                record.pr_affiliation_society_number),
                            record.mr_affiliation_society_number,
                            SocietyField().verbose(
                                record.mr_affiliation_society_number),
                            record.sr_affiliation_society_number,
                            SocietyField().verbose(
                                record.sr_affiliation_society_number)
                        )
                        if d in combinations:
                            combinations[d] += 1
                        else:
                            combinations[d] = 1
        yield (
            'PR CODE', 'PR NAME',
            'MR CODE', 'MR NAME',
            'SR CODE', 'SR NAME',
            'COUNT'
        )
        keys = list(combinations.keys())
        keys.sort(
            key=lambda x: (x[0] or '') + (x[2] or '')
        )
        for key in keys:
            yield list(key) + [combinations[key]]

    def post(self, request, *args, **kwargs):
        form = FileForm(request.POST, request.FILES)
        sorted_combinations = None
        if form.is_valid():
            f = request.FILES['file']
            try:
                edi_file = EdiFile(f)
                if isinstance(edi_file, Cwr2File):
                    title = (
                        f'{f.name} by '
                        f'Sender: {edi_file.get_header().submitter_name}')
                    sorted_combinations = list(self.process_cwr2(edi_file))
                else:
                    title = 'Not a CWR file'
            except Exception as e:
                title = str(e)
                raise
        else:
            edi_file = None
            title = 'List societies from a CWR file'
        return render(request, 'file.html', {
            'title': title,
            'form': form,
            'table': sorted_combinations
        })