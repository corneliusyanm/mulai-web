from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from accounts.models import Member
from .models import Visit

def check_in_page(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            member = Member.objects.get(email=email)
            visit = Visit.objects.create(
                member=member,
                check_in_time=timezone.now()
            )
            messages.success(request, f'Welcome, {member.name}! Check-in successful.')
            
            # Store email in session for future quick check-ins
            request.session['member_email'] = email
            return redirect('check_in_success')
        except Member.DoesNotExist:
            messages.error(request, 'Member not found. Please check your email.')
            return redirect('check_in_page')
    
    # If member email is in session, show quick check-in page
    member_email = request.session.get('member_email')
    if member_email:
        try:
            member = Member.objects.get(email=member_email)
            return render(request, 'visits/quick_check_in.html', {'member': member})
        except Member.DoesNotExist:
            request.session.pop('member_email', None)
    
    return render(request, 'visits/check_in.html')

def check_in_success(request):
    return render(request, 'visits/check_in_success.html')

def check_out_page(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            member = Member.objects.get(email=email)
            # Find the latest unchecked-out visit
            visit = Visit.objects.filter(
                member=member,
                check_out_time__isnull=True
            ).latest('check_in_time')
            
            visit.check_out_time = timezone.now()
            visit.save()
            
            messages.success(request, f'Goodbye, {member.name}! Check-out successful.')
            return redirect('check_out_success')
        except Member.DoesNotExist:
            messages.error(request, 'Member not found. Please check your email.')
        except Visit.DoesNotExist:
            messages.error(request, 'No active check-in found.')
        return redirect('check_out_page')
    
    # If member email is in session, show quick check-out page
    member_email = request.session.get('member_email')
    if member_email:
        try:
            member = Member.objects.get(email=member_email)
            return render(request, 'visits/quick_check_out.html', {'member': member})
        except Member.DoesNotExist:
            request.session.pop('member_email', None)
    
    return render(request, 'visits/check_out.html')

def check_out_success(request):
    return render(request, 'visits/check_out_success.html')

def forget_member(request):
    request.session.pop('member_email', None)
    return redirect('check_in_page')
