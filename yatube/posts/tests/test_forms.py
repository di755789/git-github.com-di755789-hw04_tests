from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..forms import PostForm
from ..models import Group, Post

User = get_user_model()


class FormsTests(TestCase):
    GROUP_TITLE = 'Тестовая группа'
    GROUP_SLUG = 'Test_group'
    GROUP_DESCRIPTION = 'Описание группы'
    GROUP_ID = 1
    GROUP_ID_AFTER_EDIT = ''
    USER = 'User_not_author'
    AUTHOR = 'TestUser'
    POST_TEXT = 'Тестовый пост для тестов'
    POST_TEXT_AFTER_EDIT = 'Тестовый пост для тестов edited'
    POST_ID = 1
    NEW_POST_ID = 2

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username=cls.AUTHOR)
        cls.group = Group.objects.create(
            title=cls.GROUP_TITLE,
            slug=cls.GROUP_SLUG,
            description=cls.GROUP_DESCRIPTION,
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text=cls.POST_TEXT,
            group=cls.group,
        )
        cls.form = PostForm()

    def setUp(self):
        self.user = User.objects.create_user(username=self.USER)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.author)

    def test_post_create_form(self):
        """Валидная форма создает запись в Post"""
        post_count = Post.objects.count()
        form_fields = {
            'text': self.POST_TEXT,
            'group': self.GROUP_ID,
        }
        response = self.authorized_client_author.post(
            reverse('posts:post_create'),
            data=form_fields,
        )
        self.assertRedirects(response,
                             reverse('posts:profile',
                                     kwargs={'username': self.AUTHOR}))
        self.assertEqual(Post.objects.count(), post_count + 1)
        new_post = Post.objects.get(id=self.NEW_POST_ID)
        self.assertEqual(new_post.text, self.POST_TEXT)
        self.assertEqual(new_post.group.id, self.GROUP_ID)

    def test_post_edit_form(self):
        """Валидная форма изменяет запись в Post"""
        posts_count = Post.objects.count()
        form_data = {
            'text': self.POST_TEXT_AFTER_EDIT,
            'group': self.GROUP_ID_AFTER_EDIT,
        }
        response = self.authorized_client_author.post(
            reverse('posts:post_edit', kwargs={'post_id': self.POST_ID}),
            data=form_data,
        )
        self.assertRedirects(response,
                             reverse('posts:post_detail',
                                     kwargs={'post_id': self.POST_ID}))
        self.assertEqual(Post.objects.count(), posts_count)
        edited_post = Post.objects.get(id=self.POST_ID)
        self.assertEqual(edited_post.text, self.POST_TEXT_AFTER_EDIT)
        self.assertIsNone(edited_post.group)
