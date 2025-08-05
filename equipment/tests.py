from django.test import TestCase
from django.urls import reverse
from .models import Equipment


class EquipmentModelTest(TestCase):
    def test_equipment_creation(self):
        """
        Test that an Equipment object is created with a slug.
        """
        equipment = Equipment.objects.create(
            name="Test Lat Pulldown",
            video_link="https://www.youtube.com/watch?v=12345",
        )
        self.assertEqual(equipment.name, "Test Lat Pulldown")
        self.assertEqual(equipment.slug, "test-lat-pulldown")

    def test_youtube_embed_url(self):
        """
        Test the get_youtube_embed_url method with different URL formats.
        """
        urls = {
            "standard": "https://www.youtube.com/watch?v=abcdef123",
            "shortened": "https://youtu.be/abcdef123",
            "embed": "https://www.youtube.com/embed/abcdef123",
        }
        expected_url = "https://www.youtube.com/embed/abcdef123"

        for name, url in urls.items():
            equipment = Equipment(name=name, video_link=url)
            self.assertEqual(equipment.get_youtube_embed_url(), expected_url)

    def test_youtube_video_id_extraction(self):
        """
        Test the get_youtube_video_id method with different URL formats.
        """
        urls = {
            "standard": "https://www.youtube.com/watch?v=abcdef123",
            "shortened": "https://youtu.be/abcdef123",
            "embed": "https://www.youtube.com/embed/abcdef123",
            "with_params": "https://www.youtube.com/watch?v=abcdef123&t=30s",
        }
        expected_id = "abcdef123"

        for name, url in urls.items():
            equipment = Equipment(name=name, video_link=url)
            self.assertEqual(equipment.get_youtube_video_id(), expected_id)

    def test_youtube_thumbnail_url(self):
        """
        Test the get_youtube_thumbnail_url method.
        """
        equipment = Equipment(
            name="Test Equipment",
            video_link="https://www.youtube.com/watch?v=abcdef123",
        )

        # Test default quality
        expected_default = "https://img.youtube.com/vi/abcdef123/hqdefault.jpg"
        self.assertEqual(equipment.get_youtube_thumbnail_url(), expected_default)

        # Test specific quality
        expected_maxres = "https://img.youtube.com/vi/abcdef123/maxresdefault.jpg"
        self.assertEqual(
            equipment.get_youtube_thumbnail_url("maxresdefault"), expected_maxres
        )


class EquipmentViewsTest(TestCase):
    def setUp(self):
        self.equipment1 = Equipment.objects.create(
            name="Chest Press",
            muscle_group="Chest",
            video_link="https://www.youtube.com/watch?v=chest",
        )
        self.equipment2 = Equipment.objects.create(
            name="Bicep Curl",
            muscle_group="Arms",
            video_link="https://www.youtube.com/watch?v=bicep",
        )

    def test_equipment_list_view(self):
        """
        Test the equipment list view.
        """
        response = self.client.get(reverse("equipment:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chest Press")
        self.assertContains(response, "Bicep Curl")
        self.assertIn("grouped_equipments", response.context)
        self.assertIn("Chest", response.context["grouped_equipments"])

    def test_equipment_detail_view(self):
        """
        Test the equipment detail view.
        """
        response = self.client.get(
            reverse("equipment:detail", kwargs={"slug": self.equipment1.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chest Press")

    def test_equipment_detail_view_not_found(self):
        """
        Test that the detail view returns a 404 for a non-existent slug.
        """
        response = self.client.get(
            reverse("equipment:detail", kwargs={"slug": "non-existent-slug"})
        )
        self.assertEqual(response.status_code, 404)
