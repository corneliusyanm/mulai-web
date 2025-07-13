from django.shortcuts import render, get_object_or_404
from .models import Equipment

# Create your views here.


def equipment_list(request):
    equipments = Equipment.objects.all()
    return render(request, "equipment/list.html", {"equipments": equipments})


def equipment_detail(request, slug):
    equipment = get_object_or_404(Equipment, slug=slug)
    return render(request, "equipment/detail.html", {"equipment": equipment})
