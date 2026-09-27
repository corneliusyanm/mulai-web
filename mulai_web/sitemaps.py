"""sitemap.xml and robots.txt: the public pages, and where to find them.

Only pages a stranger can open and would want to land on from a search. Member
pages (/akun, /kelas, /papan) sit behind a login and would only ever show a
search visitor the login form.
"""

from django.contrib.sitemaps import Sitemap
from django.http import HttpResponse
from django.urls import reverse
from django.views.decorators.cache import cache_control

from equipment.models import Equipment
from homepage import business
from nutrition import content as nutrition_content


class _CanonicalSitemap(Sitemap):
    """Every URL on the bare https domain, whichever host asked for the sitemap."""

    protocol = "https"

    def get_domain(self, site=None):
        return business.SITE_DOMAIN


class PagesSitemap(_CanonicalSitemap):
    def items(self):
        return [
            ("home", 1.0, "weekly"),
            ("equipment:list", 0.7, "monthly"),
            ("nutrition:index", 0.6, "monthly"),
            ("classes:class_rules", 0.4, "monthly"),
        ]

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]

    def changefreq(self, item):
        return item[2]


class EquipmentSitemap(_CanonicalSitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return Equipment.objects.order_by("name")

    def location(self, item):
        return reverse("equipment:detail", args=[item.slug])

    def lastmod(self, item):
        return item.updated_at


class NutritionSitemap(_CanonicalSitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return [chapter["slug"] for chapter in nutrition_content.chapters()]

    def location(self, item):
        return reverse("nutrition:chapter", args=[item])


SITEMAPS = {
    "pages": PagesSitemap,
    "alat": EquipmentSitemap,
    "gizi": NutritionSitemap,
}

# Pages that are private or only make sense to a signed-in member.
ROBOTS_DISALLOW = ["/admin/", "/akun/", "/check-in/", "/check-out/", "/forget-member/"]


@cache_control(max_age=86400, public=True)
def robots_txt(request):
    lines = ["User-agent: *"]
    lines += [f"Disallow: {path}" for path in ROBOTS_DISALLOW]
    lines += ["", f"Sitemap: {business.SITE_URL}/sitemap.xml", ""]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")
