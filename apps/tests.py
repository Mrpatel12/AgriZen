from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from .models import Farm, Crop, Inventory

User = get_user_model()

class AgriZenAuthTests(APITestCase):

    def test_user_registration(self):
        url = reverse('register')
        data = {
            'email': 'farmer_test@agrizen.com',
            'password': 'test_secure_password123',
            'role': 'FARMER'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.filter(email='farmer_test@agrizen.com').exists(), True)

    def test_user_login(self):
        # Create user
        user = User.objects.create_user(email='test_login@agrizen.com', password='mypassword123')
        url = reverse('token_obtain_pair')
        data = {
            'email': 'test_login@agrizen.com',
            'password': 'mypassword123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)


class AgriZenBusinessTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(email='farmer@agrizen.com', password='password123', role='FARMER')
        # Login to obtain token
        login_url = reverse('token_obtain_pair')
        login_resp = self.client.post(login_url, {'email': 'farmer@agrizen.com', 'password': 'password123'}, format='json')
        self.token = login_resp.data['access']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)
        
        self.farm = Farm.objects.create(name='Sunny Valley', location='California', size=150.5, owner=self.user)

    def test_create_crop(self):
        url = reverse('crop-list')
        data = {
            'farm': self.farm.id,
            'name': 'Corn',
            'variety': 'Sweet Corn',
            'status': 'PLANTED',
            'planting_date': '2026-06-24',
            'yield_quantity': 0,
            'yield_unit': 'kg'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Crop.objects.filter(name='Corn').count(), 1)

    def test_inventory_low_stock_notification(self):
        # Setting quantity below low stock threshold to trigger low stock notification
        url = reverse('inventory-list')
        data = {
            'farm': self.farm.id,
            'item_name': 'Super Fertilizer',
            'category': 'FERTILIZERS',
            'quantity': 5.0,
            'unit': 'kg',
            'low_stock_threshold': 10.0
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check if alert notification was created
        from .models import Notification
        notifications = Notification.objects.filter(user=self.user, type='LOW_STOCK')
        self.assertEqual(notifications.exists(), True)
        self.assertIn('Low Stock Alert', notifications.first().message)
