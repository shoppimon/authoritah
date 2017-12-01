from collections import namedtuple
import pytest

from authoritah import Authorizer

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


def owner_role(user, obj):
    return 'admin' if user.id == obj.created_by else 'viewer'


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

    @az.context_role_provider(owner_role)
    class ProtectedArticle(Article):
        pass

    article = ProtectedArticle(created_by=1234)
    assert az.is_allowed('article_delete', article)
    assert az.is_allowed('article_view', article)

    other_article = ProtectedArticle(created_by=5678)
    assert not az.is_allowed('article_delete', other_article)
    assert az.is_allowed('article_view', other_article)


def test_object_permissions_without_inheritance():
    az = Authorizer(default_permissions)

    @az.context_role_provider(lambda u, o: 'user_admin' if same_user(u, o) else None)
    class ProtectedUser(User):
        pass

    user = ProtectedUser(1234, ['editor'])
    other_user = ProtectedUser(5678, ['viewer'])

    az.identity_provider(lambda: user)
    az.default_role_provider(lambda u, _: u.roles)

    assert az.is_allowed('user_view', user)
    assert az.is_allowed('user_edit', user)

    assert az.is_allowed('user_view', other_user)
    assert not az.is_allowed('user_edit', other_user)
