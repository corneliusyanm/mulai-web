from django.db import models
from accounts.models import Member

class Visit(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    check_in_time = models.DateTimeField(auto_now_add=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-check_in_time']
