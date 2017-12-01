from collections import namedtuple
import pytest

from authoritah import Authorizer

User = namedtuple('User', ['id', 'roles'])

default_permissions = {
    "viewer": {"article_list", "article_view", "comment_create"},
    "editor": {"parents": "viewer",
               "grants": {"article_create"}},
    "admin": {"parents":  "editor",
              "grants": {"article_edit", "article_delete", "comment_edit",
                         "comment_delete", "user_create"}}
}


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
