from django import forms


class SubmissionForm(forms.Form):
    company_name = forms.CharField(
        label='Company name', max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. VetBill'}),
    )
    tagline = forms.CharField(
        label='Tagline', max_length=140,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Stripe for vet clinics'}),
    )
    pitch = forms.CharField(
        label='Pitch — what will the company make? (YC-style)',
        widget=forms.Textarea(attrs={'class': 'form-textarea', 'rows': 6,
            'placeholder': 'Customers, problem, traction, revenue, why now, biggest risk…'}),
    )
    product = forms.CharField(
        label='Product (optional)', required=False,
        widget=forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
    )
    founders_blurb = forms.CharField(
        label='Founders (optional)', required=False, max_length=500,
        widget=forms.TextInput(attrs={'class': 'form-input',
            'placeholder': 'e.g. Ex-Square payments engineer + vet tech cofounder'}),
    )
    whats_new = forms.CharField(label="What's new (optional)", required=False,
        widget=forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}))
    competitors = forms.CharField(label='Competitors / substitutes (optional)', required=False,
        widget=forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}))
    insight = forms.CharField(label="Insight — what you understand that others don't (optional)",
        required=False, widget=forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}))
    batch = forms.CharField(label='Batch (optional, e.g. W26)', required=False, max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-input'}))
    is_public = forms.BooleanField(
        label='List publicly on the leaderboard (free). Uncheck for a private rating (hidden).',
        required=False, initial=True,
    )

    def clean_company_name(self):
        return self.cleaned_data['company_name'].strip()

    def clean_pitch(self):
        pitch = self.cleaned_data['pitch'].strip()
        if len(pitch) < 40:
            raise forms.ValidationError('Give us a real pitch — at least a few sentences (40+ chars).')
        return pitch[:2000]
