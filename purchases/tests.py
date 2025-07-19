from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Product, Sale, SaleItem
from accounts.models import Member


class PurchaseModelTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="testuser", password="password")
        self.member = Member.objects.create(
            name="Sale Member",
            email="salemember@example.com",
            phone_number="6289876543210",
            gender="F",
            age=28,
            height=165,
            weight=58,
            years_of_working_out="1",
            goals="Stay fit",
            know_mulai_gym_from="friends",
        )
        self.product1 = Product.objects.create(name="Protein Shake", price=50000)
        self.product2 = Product.objects.create(name="Energy Bar", price=25000)

    def test_product_creation(self):
        """
        Test that a Product can be created successfully.
        """
        self.assertEqual(self.product1.name, "Protein Shake")
        self.assertEqual(self.product1.price, 50000)

    def test_sale_creation_and_total_amount_update(self):
        """
        Test that a Sale and its items are created and the total amount is updated correctly.
        """
        sale = Sale.objects.create(
            created_by=self.user,
            member=self.member,
            payment_method="QRIS",
        )
        SaleItem.objects.create(sale=sale, product=self.product1, quantity=2)
        SaleItem.objects.create(sale=sale, product=self.product2, quantity=1)

        # Manually trigger the update
        sale.update_total_amount()

        expected_total = (50000 * 2) + (25000 * 1)
        self.assertEqual(sale.total_amount, expected_total)

    def test_sale_item_price_at_purchase(self):
        """
        Test that the price_at_purchase is correctly set on the SaleItem.
        """
        sale = Sale.objects.create(created_by=self.user, payment_method="CASH")
        sale_item = SaleItem.objects.create(
            sale=sale, product=self.product1, quantity=1
        )
        self.assertEqual(sale_item.price_at_purchase, self.product1.price)

        # Test that the price remains the same even if the product price changes
        self.product1.price = 60000
        self.product1.save()
        self.assertNotEqual(sale_item.price_at_purchase, self.product1.price)
        self.assertEqual(sale_item.price_at_purchase, 50000)
