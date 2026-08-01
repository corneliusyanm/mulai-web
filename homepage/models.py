from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ReviewSummary(models.Model):
    """The Google rating badge shown above the testimonials on the homepage.

    One row, edited by hand. The Places API caps a Place Details response at 5
    reviews and needs a billing-enabled key, which buys nothing here: the count
    only ever grows, so a number that is a few weeks behind is harmless, and the
    reviews themselves are picked by hand anyway (see ``Testimonial``).
    """

    rating = models.DecimalField(
        "Rating Google",
        max_digits=2,
        decimal_places=1,
        default=5.0,
        help_text="Misal 5.0",
    )
    review_count = models.PositiveIntegerField(
        "Jumlah ulasan",
        default=0,
        help_text="Jumlah ulasan di Google Maps.",
    )
    maps_url = models.URLField(
        "Link Google Maps",
        max_length=300,
        help_text="Link ke listing Google Maps Mulai Gym.",
    )
    updated_at = models.DateTimeField("Terakhir diperbarui", auto_now=True)

    class Meta:
        verbose_name = "Ringkasan Ulasan Google"
        verbose_name_plural = "Ringkasan Ulasan Google"

    def __str__(self):
        return f"{self.rating} dari {self.review_count} ulasan"

    @classmethod
    def get_solo(cls):
        """The single summary row, or None when nobody has filled it in yet."""
        return cls.objects.first()

    @property
    def rating_display(self):
        """Rating with a comma, the way it is written in Indonesian: 5,0."""
        return f"{self.rating}".replace(".", ",")


class Testimonial(models.Model):
    """One member review, picked by hand to show on the homepage.

    Curated rather than pulled from an API: with 142 reviews on the listing, the
    ones worth showing are the ones that say the place is good for beginners,
    not whichever 5 an API happens to return.
    """

    author_name = models.CharField(
        "Nama",
        max_length=80,
        help_text="Nama seperti yang tertulis di ulasan. Boleh nama depan saja.",
    )
    rating = models.PositiveSmallIntegerField(
        "Rating",
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    text = models.TextField(
        "Ulasan",
        help_text="Tulis apa adanya, jangan diedit-edit.",
    )
    review_url = models.URLField(
        "Link ulasan",
        max_length=300,
        blank=True,
        help_text="Opsional. Link ke ulasan aslinya di Google Maps.",
    )
    is_active = models.BooleanField(
        "Tayang",
        default=True,
        help_text="Hilangkan centang untuk menyembunyikan tanpa menghapus.",
    )
    priority = models.IntegerField(
        "Prioritas",
        default=0,
        help_text="Makin besar, makin depan.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ulasan Member"
        verbose_name_plural = "Ulasan Member"
        ordering = ["-priority", "-created_at"]

    def __str__(self):
        return f"{self.author_name} ({self.rating}/5)"

    @property
    def initial(self):
        return self.author_name.strip()[:1].upper()

    @property
    def stars(self):
        """Range for the template to loop over, so it can draw filled stars."""
        return range(self.rating)

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True)
