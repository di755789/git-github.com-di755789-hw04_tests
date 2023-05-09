from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django import forms

import tempfile
import shutil
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from posts.pagination import POSTS_PER_PAGE
from ..models import Comment, Follow, Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTests(TestCase):

    small_gif = (b'\x47\x49\x46\x38\x39\x61\x02\x00'
                 b'\x01\x00\x80\x00\x00\x00\x00\x00'
                 b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
                 b'\x00\x00\x00\x2C\x00\x00\x00\x00'
                 b'\x02\x00\x01\x00\x00\x02\x02\x0C'
                 b'\x0A\x00\x3B'
                 )
    uploaded = SimpleUploadedFile(
        name='small.gif',
        content=small_gif,
        content_type='image/gif',
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Test_group',
            description='Описание группы',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост для тестов',
            group=cls.group,
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.guest_client = Client()
        self.authorized_client2 = Client()

    def post_check(self, page_obj):
        """Проверка правильности заполнения поста."""
        self.assertEqual(page_obj.pk, self.post.pk)
        self.assertEqual(page_obj.text, self.post.text)
        self.assertEqual(page_obj.author, self.post.author)
        self.assertEqual(page_obj.group, self.group)
        self.assertEqual(page_obj.image, f'posts/{self.uploaded}')

    def group_check(self, group_obj):
        """Проверка правильности отображения информации о группе."""
        self.assertEqual(group_obj.title, self.group.title)
        self.assertEqual(group_obj.slug, self.group.slug)
        self.assertEqual(group_obj.description, self.group.description)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует правильный шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}
                    ): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': self.user.username}
                    ): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.pk},
                    ): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/post_create.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.pk}
                    ): 'posts/post_create.html',
        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.post_check(response.context['page_obj'][0])
        self.assertEqual(len(response.context['page_obj'].object_list), 1)

    def test_group_posts_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': PostViewsTests.group.slug}
            )
        )
        self.post_check(response.context.get('post'))
        self.group_check(response.context.get('group'))

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}))
        self.post_check(response.context.get('post'))
        Comment.objects.create(
            post=self.post,
            author=self.user,
            text='Test comment'
        )
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        comment = response.context['comments'][0]
        self.assertIsInstance(comment, Comment)
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.post, self.post)
        self.assertEqual(response.context['comments'].count(), 1)

    def test_post_create_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'group': forms.fields.ChoiceField,
            'text': forms.fields.CharField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_create(edit) сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit',
                    kwargs={'post_id': PostViewsTests.post.pk})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': self.user.username}
                    )
        )
        self.post_check(response.context.get('post'))
        self.assertEqual(response.context['author'], self.user)

    def test_group_posts_not_mixing(self):
        """Посты не попадают в чужие группы."""
        fakegroup = Group.objects.create(
            title='title',
            slug='fakeslug',
            description='description',
        )
        response = self.authorized_client.get(reverse(
            'posts:group_list', kwargs={'slug': fakegroup.slug}
        ))
        fakegroup_posts = response.context['page_obj']

        self.assertNotIn(self.post, fakegroup_posts)

    def test_index_cache(self):
        """Тест кэша главной страницы."""
        post = Post.objects.create(
            text='Test text',
            author=self.user,
            group=self.group
        )
        response = self.authorized_client.get(reverse('posts:index')).content
        post.delete()
        response_post_delete = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertEqual(response, response_post_delete)
        cache.clear()
        response_clear_cache = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertNotEqual(response, response_clear_cache)

    def test_authorized_follow(self):
        """Авторизованный пользователь может
        подписываться на других пользователей
        """
        Follow.objects.create(
            user=self.user,
            author=self.post.author
        )
        self.authorized_client.post(
            reverse('posts:profile_follow', kwargs={
                'username': self.post.author.username})
        )
        self.assertEqual(Follow.objects.count(), 1)
        self.assertEqual(Follow.objects.latest('id').author, self.user)

    def test_authorized_unfollow(self):
        """Авторизованный пользователь
        может отписаться от автора
        """
        Follow.objects.create(
            user=self.user,
            author=self.post.author
        )
        response = self.authorized_client.post(
            reverse('posts:profile_unfollow', kwargs={
                'username': self.post.author.username})
        )
        self.assertEqual(Follow.objects.count(), 0)
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.post.author.username})
        )

    def test_guest_could_not_follow_author(self):
        """Незарегистрированный пользователь
        не может подписаться на автора
        """
        guest_redirect_url = (
            f'/auth/login/?next=/profile/{self.post.author.username}/follow/'
        )
        response = self.guest_client.post(reverse(
            'posts:profile_follow', kwargs={
                'username': self.post.author.username})
        )
        self.assertEqual(Follow.objects.count(), 0)
        self.assertRedirects(response, guest_redirect_url)

    def test_follow_context(self):
        """Проверяем, что новая запись пользователя появляется
        в ленте тех, кто на него подписан"""
        Follow.objects.create(
            user=self.user,
            author=self.post.author
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        first_object = response.context['page_obj'][0]
        self.assertEqual(len(response.context['page_obj']), 1)
        self.assertIsInstance(first_object, Post)
        self.assertEqual(first_object.author, self.post.author)
        self.assertEqual(first_object.group, self.group)
        self.assertContains(response, self.post)

    def test_unfollow_context(self):
        """Новая запись пользователя не появляется
        в ленте тех, кто на него не подписан
        """
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['page_obj']), 0)
        self.assertNotContains(response, self.post)


class PostViewsPaginatorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Test_group',
            description='Описание группы'
        )
        bulk_size = 13
        posts = [
            Post(
                text=f'Тестовый пост для тестов {post_num}',
                author=cls.user,
                group=cls.group
            )
            for post_num in range(bulk_size)
        ]
        Post.objects.bulk_create(posts, bulk_size)

    def setUp(self):
        self.paginator_length = POSTS_PER_PAGE
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.index = reverse('posts:index')
        self.profile = reverse('posts:profile', kwargs={
            'username': f'{self.user.username}'
        })
        self.group_list = reverse('posts:group_list', kwargs={
            'slug': f'{self.group.slug}'
        })

    def test_paginator(self):
        """Проверяем паджинатор на index, profile и group_posts."""
        pages_for_test = [self.index, self.profile, self.group_list]
        posts_count = Post.objects.count()
        second_page_posts_count = posts_count - self.paginator_length
        for page in pages_for_test:
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                response2 = self.authorized_client.get(page + '?page=2')
                self.assertEqual(
                    len(response.context['page_obj']),
                    self.paginator_length
                )
                self.assertEqual(
                    len(response2.context['page_obj']),
                    second_page_posts_count
                )
