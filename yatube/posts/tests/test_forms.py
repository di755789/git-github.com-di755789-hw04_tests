from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..forms import PostForm
from ..models import Comment, Group, Post

User = get_user_model()


class FormsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='TestUser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Test_group',
            description='Описание группы',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Test post text',
            group=cls.group,
        )
        cls.form = PostForm()

    def setUp(self):
        self.user = User.objects.create_user(username='User')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.author)
        self.guest_client = Client()

    def test_post_create_form(self):
        """Валидная форма создает запись в Post."""
        post_count = Post.objects.count()
        form_fields = {
            'text': self.post.text,
            'group': self.group.id,
        }
        response = self.authorized_client_author.post(
            reverse('posts:post_create'),
            data=form_fields,
        )
        self.assertRedirects(response,
                             reverse('posts:profile',
                                     kwargs={'username': self.author}))
        self.assertEqual(Post.objects.count(), post_count + 1)
        new_post = Post.objects.get(id=self.post.pk)
        self.assertEqual(new_post.text, self.post.text)
        self.assertEqual(new_post.group.id, self.group.id)

    def test_post_edit_form(self):
        """Валидная форма изменяет запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Test text edited',
            'group': '',
        }
        response = self.authorized_client_author.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form_data,
        )
        self.assertRedirects(response,
                             reverse('posts:post_detail',
                                     kwargs={'post_id': self.post.pk}))
        self.assertEqual(Post.objects.count(), posts_count)
        edited_post = Post.objects.get(id=self.post.pk)
        self.assertEqual(edited_post.text, 'Test text edited')
        self.assertIsNone(edited_post.group)

    def test_add_comment(self):
        """Валидная форма создает запись в Comment."""
        text = 'Test comment'
        form_data = {'text': text}
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
        )
        comment = Comment.objects.latest('created')
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(comment.text, text)
        self.assertEqual(comment.author, self.user)
        self.assertRedirects(
            response, reverse('posts:post_detail',
                              kwargs={'post_id': self.post.pk})
        )

    def test_access_commenting(self):
        """Неавторизованный пользователь не может комментировать"""
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data={'text': 'Test comment'}
        )
        self.assertRedirects(
            response,
            f'/auth/login/?next=/posts/{self.post.pk}/comment/'
        )
