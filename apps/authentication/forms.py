from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, EducatorProfile
from apps.courses.models import Category


class StudentRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}))

    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone', 'selected_category', 'password']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Full Name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email Address'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Contact Number'}),
            'selected_category': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        cpw = cleaned_data.get('confirm_password')
        if pw and cpw and pw != cpw:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'student'
        if commit:
            user.save()
        return user


class EducatorRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}))
    primary_category = forms.ModelChoiceField(
        queryset=Category.objects.all(), 
        empty_label="Select Primary Course/Category",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    subjects = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Other Subjects (e.g. Math, Physics)'}))
    institute_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Institute or Coaching Center Name'}))
    experience_years = forms.IntegerField(min_value=0, initial=0)
    bio = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))
    qualification = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone', 'password']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Full Name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email Address'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Contact Number'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        cpw = cleaned_data.get('confirm_password')
        if pw and cpw and pw != cpw:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'educator'
        user.is_approved = False  # Requires admin approval
        if commit:
            user.save()
            EducatorProfile.objects.create(
                user=user,
                primary_category=self.cleaned_data.get('primary_category'),
                institute_name=self.cleaned_data.get('institute_name', ''),
                subjects=self.cleaned_data.get('subjects', ''),
                experience_years=self.cleaned_data.get('experience_years', 0),
                bio=self.cleaned_data.get('bio', ''),
                qualification=self.cleaned_data.get('qualification', ''),
            )
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Email Address'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))


class EducatorProfileForm(forms.ModelForm):
    class Meta:
        model = EducatorProfile
        fields = ['bio', 'subjects', 'experience_years', 'qualification',
                  'hourly_rate', 'website', 'linkedin', 'cover_image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class UserAvatarForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['full_name', 'phone', 'avatar']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Your registered email'}))


class ResetPasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'New Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}))

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        cpw = cleaned_data.get('confirm_password')
        if pw and cpw and pw != cpw:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data
