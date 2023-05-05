from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django import forms

from posts.pagination import POSTS_PER_PAGE
from ..models import Group, Post

User = get_user_model()


class PostViewsTests(TestCase):
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
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def post_check(self, page_obj):
        """Проверка правильности заполнения поста."""
        self.assertEqual(page_obj.pk, self.post.pk)
        self.assertEqual(page_obj.text, self.post.text)
        self.assertEqual(page_obj.author, self.post.author)
        self.assertEqual(page_obj.group, self.group)

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
                    kwargs={'slug': f'{PostViewsTests.group.slug}'}
                    ): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': f'{PostViewsTests.user}'}
                    ): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': f'{int(PostViewsTests.post.pk)}'},
                    ): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/post_create.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': f'{int(PostViewsTests.post.pk)}'}
                    ): 'posts/post_create.html',
        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.post_check(response.context.get('post'))
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

    def test_post_create_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'group': forms.fields.ChoiceField,
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
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': PostViewsTests.user.username}
                    )
        )
        self.post_check(response.context.get('post'))
        self.assertEqual(response.context['author'], PostViewsTests.user)

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

        fakegroup.delete()


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
