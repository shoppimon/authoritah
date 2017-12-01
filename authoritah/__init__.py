"""Respect my authoritah!
"""

from builtins import str
from six import iteritems


class Authorizer(object):

    def __init__(self, permissions, identity_provider=None,
                 default_role_provider=None, allow_by_default=False):
        self._roles = self._process_permissions(permissions)
        self._identity_provider = identity_provider
        self._default_role_provider = default_role_provider
        self._role_providers = {}
        self._allow_by_default = allow_by_default

    def is_allowed(self, permission, context=None, identity=None):
        """Check if user is allowed to perform the specified action
        """
        if identity is None and self._identity_provider:
            identity = self._identity_provider()

        if identity is None:
            return self._allow_by_default

        roles = self._resolve_roles(identity, context=context)
        permissions = self._get_permissions(roles)

        return permission in permissions

    def identity_provider(self, f):
        self._identity_provider = f
        return f

    def default_role_provider(self, f):
        self._default_role_provider = f
        return f

    def context_role_provider(self, resolver):
        def wrap(cls):
            self._role_providers[cls] = resolver
            return cls
        return wrap

    def _resolve_roles(self, identity=None, context=None):
        """Resolve user roles given a context object
        """
        if identity is None and self._identity_provider:
            identity = self._identity_provider()

        if identity is None:
            return []

        if context is not None:
            try:
                types = type(context).mro()
                for t in types:
                    if t in self._role_providers:
                        roles = self._role_providers[t](identity, context)
                        if len(roles) > 0:
                            return roles

            except (AttributeError, TypeError):
                pass

        if self._default_role_provider is None:
            return []
        else:
            return self._default_role_provider(identity, context)

    def _get_permissions(self, roles, stack=None):
        """Get set of permissions for a list of roles

        This takes care of resolving role inheritance as well
        """
        permissions = set()
        for role in roles:
            if role not in self._roles:
                continue
            role = self._roles[role]

            if len(role.parents) > 0:
                if stack is None:
                    stack = set()
                elif role in stack:
                    raise ValueError("Cyclic role inheritance detected for "
                                     "{}".format(role))

                inherited = self._get_permissions(role.parents,
                                                  stack.union(set(role.name)))
                permissions.update(inherited)
            permissions.update(role.grants)

        return permissions

    @staticmethod
    def _process_permissions(spec):
        return {n: Role.from_spec(n, s) for n, s in iteritems(spec)}


class Role(object):
    """Role representation
    """
    def __init__(self, name, grants, parents=()):
        if isinstance(parents, str):
            parents = [parents]
        self.name = name
        self.grants = set(grants)
        self.parents = set(parents) if parents else set()

    def __repr__(self):
        return '<Role {name}>'.format(name=self.name)

    @classmethod
    def from_spec(cls, name, spec):
        """Create Role object from configuration spec
        """
        if isinstance(spec, cls):
            return spec

        elif isinstance(spec, dict):
            role = cls(name,
                       grants=spec.get('grants', []),
                       parents=spec.get('parents', []))

        else:
            role = cls(name, grants=spec)

        return role


class NotAuthorized(RuntimeError):
    pass
