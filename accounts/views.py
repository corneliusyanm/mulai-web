from django.shortcuts import render, redirect
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import DetailView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from .models import Member
from .forms import MemberSignUpForm, MemberLoginForm
from payments.models import Payment
from visits.models import Visit

# Create your views here.

class MemberSignUpView(CreateView):
    model = Member
    form_class = MemberSignUpForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('signup_success')

    def form_valid(self, form):
        member = form.save()
        # Log the member in after signup
        self.request.session['member_id'] = member.id
        return super().form_valid(form)

def signup_success(request):
    return render(request, 'accounts/signup_success.html')

def member_login(request):
    if request.method == 'POST':
        form = MemberLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                member = Member.objects.get(email=email)
                request.session['member_id'] = member.id
                return redirect('member_details')
            except Member.DoesNotExist:
                messages.error(request, 'Member not found')
    else:
        form = MemberLoginForm()
    return render(request, 'accounts/login.html', {'form': form})

def member_logout(request):
    request.session.pop('member_id', None)
    return redirect('member_login')

class MemberRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        member_id = request.session.get('member_id')
        if not member_id:
            return redirect('member_login')
        return super().dispatch(request, *args, **kwargs)

class MemberDetailView(MemberRequiredMixin, DetailView):
    model = Member
    template_name = 'accounts/member_details.html'
    context_object_name = 'member'

    def get_object(self):
        return Member.objects.get(id=self.request.session['member_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member = self.get_object()
        context['recent_visits'] = Visit.objects.filter(member=member).order_by('-check_in_time')[:5]
        context['recent_payments'] = Payment.objects.filter(member=member).order_by('-payment_date')[:5]
        return context

def home(request):
    return render(request, 'home.html')
