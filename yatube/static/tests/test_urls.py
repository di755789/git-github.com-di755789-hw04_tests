from django.test import TestCase, Client
from http import HTTPStatus
from django.urls import reverse

PAGES_FOR_TEST = {
    reverse('about:author'): 'about/author.html',
    reverse('about:tech'): 'about/tech.html',
}


class StaticPagesURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_about_url_exists_at_desired_location(self):
        """Проверка доступности адресов about"""
        for page in PAGES_FOR_TEST:
            with self.subTest(page=page):
                response = self.guest_client.get(page)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_uses_correct_template(self):
        """Корректность использования шаблонов about"""
        for page, template in PAGES_FOR_TEST.items():
            with self.subTest(page=page):
                response = self.guest_client.get(page)
                self.assertTemplateUsed(response, template)
