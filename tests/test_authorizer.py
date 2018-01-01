from collections import namedtuple

import pytest

from authoritah import Authorizer, NotAuthorized
from authoritah.authorizer import NotDefinedError

User = namedtuple('User', ['id', 'roles'])
Article = namedtuple('Article', ['created_by'])

default_permissions = {
    "viewer": {"article_list", "article_view", "comment_create", "user_view"},
    "editor": {"parents": "viewer",
               "grants": {"article_create"}},
    "admin": {"parents":  "editor",
              "grants": {"article_edit", "article_delete", "comment_edit",
                         "comment_delete", "user_create"}},
    "user_admin": {"grants": {"user_edit"}}
}


def same_user(user, obj):
    return isinstance(obj, User) and user.id == obj.id


@pytest.mark.parametrize('role,permission,allowed', [
    ('viewer', 'article_create', False),
    ('viewer', 'article_list', True),
    ('viewer', 'article_delete', False),
    ('viewer', 'comment_create', True),
    ('viewer', 'comment_delete', False),
    ('editor', 'article_create', True),
    ('editor', 'comment_delete', False),
    ('editor', 'article_delete', False),
    ('editor', 'user_create', False),
    ('admin', 'article_delete', True),
    ('admin', 'article_edit', True),
    ('admin', 'user_create', True),
])
def test_default_permissions_no_context(role, permission, allowed):
    az = Authorizer(default_permissions)
    az.identity_provider(lambda: User(1234, [role]))
    az.default_role_provider(lambda u, _: u.roles)
    assert az.is_allowed(permission) == allowed


@pytest.mark.parametrize('role,permission,allowed', [
    ('editor', 'article_list', True),
    ('editor', 'comment_create', True),
    ('admin', 'article_create', True),
    ('admin', 'article_list', True),
])
def test_default_permissions_inherited_no_context(role, permission, allowed):
    az = Authorizer(default_permissions)
    az.identity_provider(lambda: User(1234, [role]))
    az.default_role_provider(lambda u, _: u.roles)
    assert az.is_allowed(permission) == allowed


def test_object_permissions():
    az = Authorizer(default_permissions)
    az.identity_provider(lambda: User(1234, ['editor']))
    az.default_role_provider(lambda u, _: u.roles)

    @az.role_provider(Article)
    def role_provider(user, obj):
        return 'admin' if user.id == obj.created_by else 'viewer'

    article = Article(created_by=1234)
    assert az.is_allowed('article_delete', article)
    assert az.is_allowed('article_view', article)

    other_article = Article(created_by=5678)
    assert not az.is_allowed('article_delete', other_article)
    assert az.is_allowed('article_view', other_article)


def test_object_permissions_set_provider():
    az = Authorizer(default_permissions)
    az.identity_provider(lambda: User(1234, ['editor']))
    az.default_role_provider(lambda u, _: u.roles)

    def get_roles(user, article):
        return ['admin'] if user.id == article.created_by else []

    az.set_role_provider(for_type=Article, provider=get_roles)

    article = Article(created_by=1234)
    assert az.is_allowed('article_delete', article)
    assert az.is_allowed('article_view', article)

    other_article = Article(created_by=5678)
    assert not az.is_allowed('article_delete', other_article)
    assert az.is_allowed('article_view', other_article)


def test_object_permissions_child_class():
    az = Authorizer(default_permissions)
    az.identity_provider(lambda: User(1234, ['editor']))
    az.default_role_provider(lambda u, _: u.roles)

    @az.role_provider(Article)
    def get_roles(user, article):
        return ['admin'] if user.id == article.created_by else []

    class ChildArticle(Article):
        pass

    article = ChildArticle(created_by=1234)
    assert az.is_allowed('article_delete', article)
    assert az.is_allowed('article_view', article)

    other_article = ChildArticle(created_by=5678)
    assert not az.is_allowed('article_delete', other_article)
    assert az.is_allowed('article_view', other_article)


def test_object_permissions_without_inheritance():
    az = Authorizer(default_permissions)

    @az.role_provider(User)
    def role_provider(user, ctx):
        return 'user_admin' if same_user(user, ctx) else None

    user = User(1234, ['editor'])
    other_user = User(5678, ['viewer'])

    az.identity_provider(lambda: user)
    az.default_role_provider(lambda u, _: u.roles)

    assert az.is_allowed('user_view', user)
    assert az.is_allowed('user_edit', user)

    assert az.is_allowed('user_view', other_user)
    assert not az.is_allowed('user_edit', other_user)


def test_class_role_provider():
    az = Authorizer(default_permissions)

    @az.class_role_provider('get_roles')
    class ProtectedUser(User):
        def get_roles(self, user):
            return 'user_admin' if same_user(self, user) else None

    user = ProtectedUser(1234, ['editor'])
    other_user = ProtectedUser(5678, ['viewer'])

    az.identity_provider(lambda: user)
    az.default_role_provider(lambda u, _: u.roles)

    # These should all pass with no problem
    assert az.is_allowed('user_view', user)
    assert az.is_allowed('user_view', other_user)
    assert az.is_allowed('user_edit', user)

    # This should not be allowed
    assert not az.is_allowed('user_edit', other_user)


def test_class_role_provider_child_class():
    az = Authorizer(default_permissions)

    @az.class_role_provider('get_roles')
    class ProtectedUser(User):
        def get_roles(self, u):
            return 'user_admin' if same_user(self, u) else None

    class SpecificUser(ProtectedUser):
        pass

    user = SpecificUser(1234, ['editor'])
    other_user = SpecificUser(5678, ['viewer'])

    az.identity_provider(lambda: user)
    az.default_role_provider(lambda u, _: u.roles)

    # These should all pass with no problem
    assert az.is_allowed('user_view', user)
    assert az.is_allowed('user_view', other_user)
    assert az.is_allowed('user_edit', user)

    # This should not be allowed
    assert not az.is_allowed('user_edit', other_user)


def test_requires_decorator():
    az = Authorizer(default_permissions)

    @az.class_role_provider('get_roles')
    class ProtectedUser(User):

        def get_roles(self, user):
            return 'user_admin' if same_user(self, user) else None

        @az.require('user_view')
        def view(self):
            return 'viewed'

        @az.require('user_edit')
        def edit(self):
            return 'edited'

    user = ProtectedUser(1234, ['editor'])
    other_user = ProtectedUser(5678, ['viewer'])

    az.identity_provider(lambda: user)
    az.default_role_provider(lambda u, _: u.roles)

    # These should all pass with no
    assert user.view() == 'viewed'
    assert user.edit() == 'edited'
    assert other_user.view() == 'viewed'

    # This should throw an exception
    with pytest.raises(NotAuthorized):
        other_user.edit()


def test_undefined_role():
    az = Authorizer(default_permissions)

    @az.class_role_provider('get_roles')
    class ProtectedUser(User):
        def get_roles(self, user):
            return 'user_admin'

    user = ProtectedUser(1234, ['non-existing-role-name'])
    az.identity_provider(lambda: user)
    az.default_role_provider(lambda u, _: u.roles)
    assert not az.is_allowed('non-existing-permission', user)
    assert not az.is_allowed('user_view', user)


def test_undefined_role_strict():
    az = Authorizer(default_permissions, strict=True)

    @az.class_role_provider('get_roles')
    class ProtectedUser(User):
        def get_roles(self, user):
            return 'user_admin'

    user = ProtectedUser(1234, ['non-existing-role-name'])
    az.identity_provider(lambda: user)
    az.default_role_provider(lambda u, _: u.roles)
    with pytest.raises(NotDefinedError):
        az.is_allowed('non-existing-permission', user)
    with pytest.raises(NotDefinedError):
        az.is_allowed('user_view', user)
