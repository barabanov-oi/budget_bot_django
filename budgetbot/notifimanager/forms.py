from django import forms

from .models import Profile

class ProfileForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = (
            'chat_id',
            'name',
            'email',
            'verify',
        )
        widgets = {
            'name': forms.TextInput,
            'verify': forms.RadioSelect,
        }