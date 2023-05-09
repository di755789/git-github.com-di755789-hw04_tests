from django.shortcuts import get_object_or_404, render
from .models import Follow, Post, Group, User
from .pagination import get_page
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from . forms import PostForm, CommentForm


def index(request):
    template = 'posts/index.html'
    page_obj = get_page(request,
                        Post.objects.select_related('author', 'group')
                        )
    context = {
        'page_obj': page_obj
    }
    return render(request, template, context)


def group_posts(request, slug):
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    page_obj = get_page(request, group.posts.all())
    context = {
        'group': group,
        'page_obj': page_obj
    }
    return render(request, template, context)


def profile(request, username):
    template = 'posts/profile.html'
    author = get_object_or_404(User, username=username)
    page_obj = get_page(request, author.posts.all())
    following = request.user.is_authenticated and (
        request.user.follower.filter(author=author).exists()
    )
    context = {
        'author': author,
        'page_obj': page_obj,
        'following': following,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, pk=post_id)
    comments = post.comments.all()
    form = CommentForm(request.POST or None)
    context = {
        'post': post,
        'form': form,
        'comments': comments,
    }
    return render(request, template, context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None,
                    files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', username=post.author)
    return render(request, 'posts/post_create.html', {'form': form})


@login_required
def post_edit(request, post_id):
    template = 'posts/post_create.html'
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id)
    form = PostForm(request.POST or None,
                    files=request.FILES or None,
                    instance=post
                    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id)
    return render(request, template, {
        'form': form, 'is_edit': True, 'post': post})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    template = 'includes/follow.html'
    following_posts = Post.objects.filter(author__following__user=request.user)
    page_obj = get_page(request, following_posts)
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    follow_author = get_object_or_404(User, username=username)
    if request.user != follow_author:
        Follow.objects.get_or_create(user=request.user, author=follow_author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    unfollow_author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=unfollow_author).delete()
    return redirect('posts:profile', username=username)
