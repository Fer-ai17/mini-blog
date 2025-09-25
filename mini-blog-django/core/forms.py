from django import forms
from .models import Post

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title", "content", "image"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Título"}),
            "content": forms.Textarea(attrs={"class": "form-control", "placeholder": "Escribe tu contenido aquí..."}),
        }
