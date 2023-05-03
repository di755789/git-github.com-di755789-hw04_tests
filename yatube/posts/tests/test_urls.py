from http import HTTPStatus
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(title='Тестовая группа',
                                         slug='test_group'
                                         )

    def setUp(self):
        self.user = User.objects.create_user(username='NoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.user_non = User.objects.create_user(username='NoPosts')
        self.authorized_client_no_posts = Client()
        self.authorized_client_no_posts.force_login(self.user_non)
        self.post = Post.objects.create(text='Тестовый текст',
                                        author=self.user
                                        )

    def test_urls_uses_correct_template(self):
        """Проверка корректности выбора шаблона."""
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{PostURLTests.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user}/': 'posts/profile.html',
            f'/posts/{int(self.post.pk)}/': 'posts/post_detail.html',
            f'/posts/{int(self.post.pk)}/edit/': 'posts/post_create.html',
            '/create/': 'posts/post_create.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_urls_uses_correct_access_guest(self):
        """Доступность адреса неавторизованному юзеру."""
        code_answer_for_users = {
            '/': HTTPStatus.OK,
            f'/group/{PostURLTests.group.slug}/': HTTPStatus.OK,
            f'/profile/{self.user}/': HTTPStatus.OK,
            f'/posts/{int(self.post.pk)}/': HTTPStatus.OK,
            f'/posts/{int(self.post.pk)}/edit/': HTTPStatus.FOUND,
            '/create/': HTTPStatus.FOUND,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
        }
        for address, code in code_answer_for_users.items():
            with self.subTest(address=address):
                cache.clear()
                response = self.client.get(address)
                self.assertEqual(response.status_code, code)

    def test_urls_uses_correct_access_auth(self):
        """Доступность адреса авторизованному юзеру."""
        code_answer_for_users = {
            '/': HTTPStatus.OK,
            f'/group/{PostURLTests.group.slug}/': HTTPStatus.OK,
            f'/profile/{self.user}/': HTTPStatus.OK,
            f'/posts/{int(self.post.pk)}/': HTTPStatus.OK,
            f'/posts/{int(self.post.pk)}/edit/': HTTPStatus.OK,
            '/create/': HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
        }
        for address, code in code_answer_for_users.items():
            with self.subTest(address=address):
                cache.clear()
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, code)

    def test_urls_uses_correct_access_auth_edit(self):
        """Адрес редактирования доступен только автору."""
        code_answer_for_users = {
            '/': HTTPStatus.OK,
            f'/group/{PostURLTests.group.slug}/': HTTPStatus.OK,
            f'/profile/{self.user}/': HTTPStatus.OK,
            f'/posts/{self.post.pk}/': HTTPStatus.OK,
            f'/posts/{self.post.pk}/edit/': HTTPStatus.FOUND,
            '/create/': HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
        }
        for address, code in code_answer_for_users.items():
            with self.subTest(address=address):
                cache.clear()
                response = self.authorized_client_no_posts.get(address)
                self.assertEqual(response.status_code, code)
