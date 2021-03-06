from django.shortcuts import render
from django import forms
from music_metadata.territories.territory import Territory
from music_metadata.territories.territory_list import TerritoryList
from django.views import View


class TerritoryForm(forms.Form):

    def get_choices():
        choices = [(None, '-')]
        choices += sorted(
            [(k, str(t)) for k, t in Territory.all_tis_n.items()],
            key=lambda x: x[1])
        return choices

    include_or_exclude = forms.ChoiceField(
        choices=[
            ('I', 'Include'),
            ('E', 'Exclude'),
        ]
    )
    territory = forms.ChoiceField(
        choices=get_choices,
        required=False
    )

    value = forms.IntegerField(
        required=False
    )


class BaseTerritoryFormset(forms.BaseFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__( *args, **kwargs)
        self.territory_list = None

    def clean(self):
        if any(self.errors):
            return
        tl = TerritoryList()
        func = tl.include
        for form in self.forms:
            if form.cleaned_data.get('value'):
                func = tl.add
        for form in self.forms:
            ie = form.cleaned_data.get('include_or_exclude')
            t = form.cleaned_data.get('territory')
            v = form.cleaned_data.get('value')
            if not t:
                continue
            try:
                if ie == 'I':
                    func(Territory.get(t), v)
                else:
                    if v:
                        form.add_error(
                            None, 'Value must be 0 or empty in excl.')
                    tl.exclude(Territory.get(t))
            except ValueError as e:
                form.add_error(None, str(e))
        self.territory_list = tl
        self.territory_list.compress()


TerritoryFormSet = forms.formset_factory(
    TerritoryForm,
    formset=BaseTerritoryFormset,
    extra=10)


class TerritoryListView(View):
    def get(self, request):
        formset = TerritoryFormSet()
        return render(request, 'territorylist.html', {
            'title': 'CIS Territory Including and Excluding',
            'formset': formset})

    def post(self, request, *args, **kwargs):
        formset = TerritoryFormSet(request.POST)
        if formset.is_valid():
            pass
        return render(request, 'territorylist.html', {
            'title': 'CIS Territory Calculations',
            'formset': formset})
