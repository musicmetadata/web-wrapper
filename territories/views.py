from django.shortcuts import render
from django import forms
from music_metadata.territories import TerritoryList, Territory
from django.views import View


class TerritoryForm(forms.Form):
    include_or_exclude = forms.ChoiceField(
        choices=[
            ('I', 'Include'),
            ('E', 'Exclude'),
        ]
    )
    territory = forms.ChoiceField(
        choices= [(None, '-')] +
            sorted(
                [(k, str(t)) for k, t  in Territory.all_tis_n.items()],
                key=lambda x: x[1] ),
        required = False
    )


class BaseTerritoryFormset(forms.BaseFormSet):
    def clean(self):
        if any(self.errors):
            return
        tl = TerritoryList()
        for form in self.forms:
            ie = form.cleaned_data.get('include_or_exclude')
            t = form.cleaned_data.get('territory')
            if not t:
                continue
            try:
                if ie == 'I':
                    tl.include(Territory.get(t))
                else:
                    tl.exclude(Territory.get(t))
            except ValueError as e:
                form.add_error(None, str(e))
        self.territory_list = tl


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
