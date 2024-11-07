from django import forms

class FileForm(forms.Form):
    archivo = forms.FileField(required=True)