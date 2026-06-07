from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, EducatorProfile, PromoCode
from apps.courses.models import Category


class StudentRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}))
    promo_code = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Educator Promo Code (Optional)'}))

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
            
        promo = cleaned_data.get('promo_code')
        if promo:
            try:
                promo_obj = PromoCode.objects.get(code=promo, is_active=True)
                self.linked_educator_obj = promo_obj.educator
            except PromoCode.DoesNotExist:
                self.add_error('promo_code', "Invalid or inactive promo code.")
                
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'student'
        if hasattr(self, 'linked_educator_obj'):
            user.linked_educator = self.linked_educator_obj
            
        if commit:
            user.save()
        return user


class EducatorRegistrationForm(forms.ModelForm):
    educator_type = forms.ChoiceField(
        choices=[('individual', 'Individual Educator'), ('institute', 'Institute')],
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_educator_type'})
    )
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}))
    primary_category = forms.ModelChoiceField(
        queryset=Category.objects.all(), 
        empty_label="Select Primary Course/Category",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    subjects = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Other Subjects (e.g. Math, Physics)'}))
    institute_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Institute or Coaching Center Name', 'id': 'id_institute_name'}))
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
            
        educator_type = cleaned_data.get('educator_type')
        institute_name = cleaned_data.get('institute_name')
        if educator_type == 'institute' and not institute_name:
            self.add_error('institute_name', "Institute name is mandatory for Institute accounts.")
            
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
                educator_type=self.cleaned_data.get('educator_type'),
                primary_category=self.cleaned_data.get('primary_category'),
                institute_name=self.cleaned_data.get('institute_name', '') if self.cleaned_data.get('educator_type') == 'institute' else '',
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
        fields = ['institute_name', 'bio', 'subjects', 'experience_years', 'qualification',
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

class SubEducatorCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    
    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone', 'password']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Full Name', 'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email Address', 'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Contact Number', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].widget.attrs.update({'class': 'form-control'})
        
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'educator'
        user.is_approved = True  # Automatically approved because institute creates them
        if commit:
            user.save()
        return user
