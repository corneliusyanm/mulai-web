from django.shortcuts import render, get_object_or_404
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from .models import Equipment
from collections import defaultdict

# Create your views here.


@cache_page(60 * 15)  # Cache for 15 minutes
def equipment_list(request):
    # Try to get cached data first
    cache_key = "equipment_grouped_list"
    grouped_equipments = cache.get(cache_key)

    if grouped_equipments is None:
        # Cache miss - fetch from database
        equipments = Equipment.objects.order_by("muscle_group", "name")
        grouped_equipments = defaultdict(list)
        for equipment in equipments:
            muscle_group = equipment.muscle_group or "Lainnya"
            grouped_equipments[muscle_group].append(equipment)

        # Convert to regular dict and cache for 1 hour
        grouped_equipments = dict(grouped_equipments)
        cache.set(cache_key, grouped_equipments, 60 * 60)

    context = {"grouped_equipments": grouped_equipments}
    return render(request, "equipment/list.html", context)


def equipment_detail(request, slug):
    equipment = get_object_or_404(Equipment, slug=slug)
    return render(request, "equipment/detail.html", {"equipment": equipment})
