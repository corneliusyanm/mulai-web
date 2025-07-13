from django.shortcuts import render, get_object_or_404
from .models import Equipment
from collections import defaultdict

# Create your views here.


def equipment_list(request):
    equipments = Equipment.objects.order_by("muscle_group", "name")
    grouped_equipments = defaultdict(list)
    for equipment in equipments:
        muscle_group = equipment.muscle_group or "Lainnya"
        grouped_equipments[muscle_group].append(equipment)
    context = {"grouped_equipments": dict(grouped_equipments)}
    return render(request, "equipment/list.html", context)


def equipment_detail(request, slug):
    equipment = get_object_or_404(Equipment, slug=slug)
    return render(request, "equipment/detail.html", {"equipment": equipment})
