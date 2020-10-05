from django.shortcuts import render
from django.template.loader import render_to_string
from django.http import (
    HttpResponse, StreamingHttpResponse, HttpResponseBadRequest)
from django import forms
from music_metadata.edi.file import EdiFile
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
try:
    from music_metadata.cwr2.file import Cwr2File
    from music_metadata.cwr2.fields import SocietyField
except ImportError:
    pass
from django.views import View
import json
import csv
from openpyxl import load_workbook, writer as excel_writer
import os


class FileForm(forms.Form):
    file = forms.FileField()


class ShowErrorsFileForm(FileForm):
    show_errors = forms.BooleanField(required=False)


class CsvOverview(View):
    class Echo:
        """An object that implements just the write method of the file-like
        interface.
        """

        def write(self, value):
            """Write the value by returning it, instead of storing in a
            buffer."""
            return value

    def get(self, request):
        """Respond to GET."""
        form = ShowErrorsFileForm
        return render(request, 'file.html', {
            'title': 'CWR 2.x to CSV - Conversion with Validation',
            'form': form})

    def stream_csv(self, edi_file, show_errors=False):
        fields = (
            'work_title',
            'submitter_work_number',
            'iswc',
            'musical_work_distribution_category',
            'version_type',
            'writers',
            'valid',
        )
        yield fields
        for group in edi_file.get_groups():
            for transaction in group.get_transactions():
                d = transaction.to_dict(1)
                out = []
                for field in fields:
                    value = d.get(field, '')
                    if isinstance(value, dict):
                        if show_errors and value.get('error'):
                            error = value.get('error')
                        else:
                            error = None
                        value = value.get('value', '')
                        if error:
                            value += f' <error: {error}>'
                    if field == 'writers':
                        last_names = []
                        for w in value:
                            lname = w.get('writer_last_name')
                            if lname:
                                if show_errors and lname.get('error'):
                                    error = lname.get('error')
                                else:
                                    error = None
                                lname = lname.get('value')
                                if lname is not None:
                                    lname = lname.strip()
                                if error:
                                    lname += f' <error: {error}>'
                            else:
                                lname = '<writer unknown>'
                            last_names.append(lname)
                        out.append(' / '.join(sorted(last_names)))
                    else:
                        out.append(value)
                yield out

    def post(self, request, *args, **kwargs):
        """Respond to POST."""
        form = ShowErrorsFileForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['file']
            edi_file = EdiFile(f)
            edi_file.seek(0)
            edi_file.reconfigure(encoding='latin1')
        else:
            return render(request, 'file.html', {
                'title': 'CWR 2.x to CSV - Conversion with Validation',
                'form': form
            })
        pseudo_buffer = self.Echo()
        writer = csv.writer(pseudo_buffer)
        response = StreamingHttpResponse(
            (writer.writerow(row) for row in self.stream_csv(
                edi_file, form.cleaned_data.get('show_errors'))),
            content_type="text/csv")
        response['Content-Disposition'] = (
            f'attachment; filename="{edi_file.name}.csv"')
        return response


class ExcelOverview(View):

    def get(self, request):
        """Respond to GET."""
        form = FileForm()
        return render(request, 'file.html', {
            'title': 'CWR 2.x to Excel - Conversion WITHOUT Validation',
            'form': form})

    def post(self, request, *args, **kwargs):
        """Respond to POST."""
        form = FileForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['file']
            edi_file = EdiFile(f)
            edi_file.seek(0)
            edi_file.reconfigure(encoding='latin1')
        else:
            return render(request, 'cwr_file_start.html', {
                'title': 'CWR 2.x to Excel - Conversion WITHOUT Validation',
                'form': form
            })
        wb = load_workbook(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'template.xlsx'))
        works = wb.get_sheet_by_name('Works')
        recordings = wb.get_sheet_by_name('Recordings')

        for group in edi_file.get_groups():
            for transaction in group.get_transactions():
                d = transaction.to_dict(1)
                work_keys = [
                    'submitter_work_number',
                    'work_title',
                    'iswc',
                    'recordings',
                    'duration',
                    'language_code',
                    'musical_work_distribution_category',
                    'version_type',
                    'other_titles',
                    'writers',
                    'performing_artists',
                    'original_publishers',
                ]
                values = []
                for key in work_keys:
                    if key == 'recordings':
                        isrcs = []
                        for recording in d['recordings']:
                            isrc = recording.get('isrc')
                            if isrc:
                                isrcs.append(isrc['value'])
                            recordings.append([
                                d.get('submitter_work_number', {}).get(
                                    'value', ''),
                                d.get('work_title').get('value', ''),
                                recording.get(
                                    'isrc', {}
                                ).get('value', ''),
                                recording.get(
                                    'release_date', {}
                                ).get('value', ''),
                                recording.get(
                                    'recording_duration', {}
                                ).get('value', ''),
                                recording.get(
                                    'album_title', {}
                                ).get('value', ''),
                                recording.get(
                                    'ean', {}
                                ).get('value', ''),
                                recording.get(
                                    'album_label', {}
                                ).get('value', ''),
                            ])
                        value = ' | '.join(isrcs)
                    elif key == 'other_titles':
                        value = ' | '.join([
                            t['title']['value'] or '' for t in
                            d[key]])
                    elif key == 'writers':
                        writer_strings = []
                        for writer in d['writers']:
                            controlled = writer.get('controlled')
                            ln = writer.get(
                                'writer_last_name',
                                {'value': '<UNKNOWN>'}
                            )['value']
                            fn = writer.get(
                                'writer_first_name', {}
                            ).get('value', '')
                            ipi_name = writer.get(
                                'writer_ipi_name_number', {}
                            ).get('value', '')
                            role = writer.get(
                                'writer_role', {}
                            ).get('value', '')
                            pr_share = writer.get(
                                'pr_ownership_share', {}
                            ).get('value', '') or 0
                            mr_share = writer.get(
                                'mr_ownership_share', {}
                            ).get('value', '') or 0
                            sr_share = writer.get(
                                'sr_ownership_share', {}
                            ).get('value', '') or 0
                            if controlled:
                                writer_strings.append(
                                    f'{ln}, {fn} [{ipi_name}] ({role}) '
                                    f'{{{pr_share * 100}%,{mr_share * 100}%'
                                    f',{sr_share * 100}%}} *'
                                )
                            else:
                                writer_strings.append(
                                    f'{ln}, {fn} [{ipi_name}] ({role}) '
                                    f'{{{pr_share * 100}%,{mr_share * 100}%'
                                    f',{sr_share * 100}%}}'
                                )
                        value = ' | '.join(writer_strings)
                    elif key == 'performing_artists':
                        artist_strings = []
                        for artist in d['performing_artists']:
                            ln = artist.get(
                                'performing_artist_name',
                                {'value': '<UNKNOWN>'}
                            )['value']
                            fn = artist.get(
                                'performing_artist_first_name', {}
                            ).get('value', '')
                            if fn:
                                artist_strings.append(
                                    f'{ ln }, { fn }'
                                )
                            else:
                                artist_strings.append(ln)
                        value = ' | '.join(artist_strings)
                    elif key == 'original_publishers':
                        publisher_strings = []
                        for publisher in d['original_publishers']:
                            controlled = publisher.get('controlled')
                            n = publisher.get(
                                'publisher_name',
                                {'value': '<UNKNOWN>'}
                            )['value']
                            ipi_name = publisher.get(
                                'publisher_ipi_name_number', {}
                            ).get('value', '')
                            role = publisher.get(
                                'publisher_role', {}
                            ).get('value', '')
                            pr_share = publisher.get(
                                'pr_ownership_share', {}
                            ).get('value', '') or 0
                            mr_share = publisher.get(
                                'mr_ownership_share', {}
                            ).get('value', '') or 0
                            sr_share = publisher.get(
                                'sr_ownership_share', {}
                            ).get('value', '') or 0

                            if controlled:
                                publisher_strings.append(
                                    f'{ n } [{ ipi_name }] ({role}) *'
                                    f'{{{pr_share * 100}%,{mr_share * 100}%'
                                    f',{sr_share * 100}%}} *'
                                )
                            else:
                                publisher_strings.append(
                                    f'{n} [{ipi_name}] ({role}) '
                                    f'{{{pr_share * 100}%,{mr_share * 100}%'
                                    f',{sr_share * 100}%}}'
                                )
                        value = ' | '.join(publisher_strings)
                    else:
                        value = d[key].get('value', '') if d.get(key) else ''
                    values.append(value)
                works.append(values)

        response = HttpResponse(
            excel_writer.excel.save_virtual_workbook(wb),
            content_type='application/vnd.ms-excel')
        s = 'attachment; filename="{}.xlsx"'.format(
            edi_file.name)
        response['Content-Disposition'] = s
        return response


class VisualValidatorView(View):

    def get(self, request):
        """Respond to GET."""
        form = FileForm()
        return render(request, 'file.html', {
            'title': 'Parsing and Visual Validation',
            'form': form})

    def stream(self, request, edi_file, title, form):
        """Yield response in streamed chunks."""
        yield render_to_string('cwr_file_start.html', {
            'title': title,
            'form': form,
            'edi_file': edi_file,
            'groups': edi_file.get_groups()
        }, request)
        for group in edi_file.get_groups():
            yield render_to_string('cwr_group_start.html', {
                'group': group
            })
            for transaction in group.get_transactions():
                yield render_to_string('cwr_transaction.html', {
                    'transaction': transaction,
                })
            yield render_to_string('cwr_group_end.html', {
                'group': group
            })
        yield render_to_string('cwr_file_end.html', {
            'edi_file': edi_file
        })

    def post(self, request, *args, **kwargs):
        """Respond to POST."""
        form = FileForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['file']
            edi_file = EdiFile(f)
            title = f'Parsing and Visual Validation: { edi_file.name }'
            response = StreamingHttpResponse(self.stream(
                request, edi_file, title, form))
            return response
        else:
            edi_file = None
            title = 'Parsing and Visual Validation'
            return render(request, 'file.html', {
                'title': title,
                'form': form,
                'edi_file': edi_file,
                'groups': edi_file.get_groups() if edi_file else []
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
            'title': 'EDI to JSON - Conversion with Validation',
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
                d = self.to_json(edi_file, int(form.cleaned_data['verbosity']))
            except Exception as e:
                return HttpResponseBadRequest('This file can not be processed.')
            response = StreamingHttpResponse(d)
            if form.cleaned_data['download']:
                response['Content-Disposition'] = (
                    f'attachment; filename="{ edi_file.name }.json"')
            response['Content-Type'] = 'application/json'
            return response
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