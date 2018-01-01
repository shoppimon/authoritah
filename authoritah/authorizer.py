"""Main authorization API
"""
from functools import wraps

from six import iteritems, string_types


class Authorizer(object):

    def __init__(self, permissions, identity_provider=None,
                 default_role_provider=None, strict=False):
        self._roles = self._process_permissions(permissions)
        self._identity_provider = identity_provider
        self._default_role_provider = default_role_provider
        self._role_providers = {}

        self.allow_by_default = False
        self.exc_class = NotAuthorized
        self.strict = strict

    def is_allowed(self, permission, context=None, identity=None):
        """Check if user is allowed to perform the specified action
        """
        if identity is None and self._identity_provider:
            identity = self._identity_provider()

        if identity is None:
            return self.allow_by_default

        roles = self._resolve_roles(identity, context=context)
        permissions = self._get_permissions(roles)

        if self.strict and permission not in permissions:
            all_permissions = self._get_permissions(self._roles.keys())
            if permission not in all_permissions:
                raise NotDefinedError('Permission %s not defined in any role' % permission)

        return permission in permissions

    def identity_provider(self, f):
        self._identity_provider = f
        return f

    def default_role_provider(self, f):
        self._default_role_provider = f
        return f

    def set_role_provider(self, for_type, provider):
        self._role_providers[for_type] = provider

    def role_provider(self, for_type):
        def wrap(f):
            self.set_role_provider(for_type, f)
            return f
        return wrap

    def class_role_provider(self, method):
        def wrap(cls):
            self.set_role_provider(cls, method)
            return cls
        return wrap

    def require(self, permission, context_obj=None, error_message=None):
        """Decorator generator for protecting methods with permission checks
        """
        def wrapper(f):
            if error_message is None:
                err = "Calling the {} method requires '{}' permission".\
                    format(f.__name__, permission)
            else:
                err = error_message

            @wraps(f)
            def wrapped(*args, **kwargs):
                if context_obj is None:
                    obj = args[0]
                else:
                    obj = context_obj

                if self.is_allowed(permission, context=obj):
                    return f(*args, **kwargs)
                else:
                    raise self.exc_class(err)

            return wrapped

        return wrapper

    def _resolve_roles(self, identity=None, context=None):
        """Resolve user roles given a context object
        """
        roles = set()

        if identity is None and self._identity_provider:
            identity = self._identity_provider()

        if identity is None:
            return roles

        if context is not None:
            types = [context]
            try:
                types += type(context).mro()
            except (AttributeError, TypeError):
                pass

            for t in types:
                try:
                    provider = self._role_providers[t]
                    roles.update(self._get_roles(provider, identity, context))
                except (TypeError, KeyError):
                    continue

        if self._default_role_provider is not None:
            roles.update(self._get_roles(self._default_role_provider,
                                         identity,
                                         context))

        return roles

    def _get_permissions(self, roles, stack=None):
        """Get set of permissions for a list of roles

        This takes care of resolving role inheritance as well
        """
        permissions = set()
        for role in roles:
            if role not in self._roles:
                if self.strict:
                    raise NotDefinedError('Role %s not defined in roles' % role)
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
    def _get_roles(cb, identity, context):
        """Get a set of normalized roles from a role provider
        """
        if isinstance(cb, string_types) and hasattr(context, cb):
            roles = getattr(context, cb)(identity)
        else:
            roles = cb(identity, context)

        if not roles or len(roles) == 0:
            return set()

        if isinstance(roles, string_types):
            return {roles}

        return set(roles)

    @staticmethod
    def _process_permissions(spec):
        return {n: Role.from_spec(n, s) for n, s in iteritems(spec)}


class Role(object):
    """Role representation
    """
    def __init__(self, name, grants, parents=()):
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
            parents = spec.get('parents', [])
            if isinstance(parents, string_types):
                parents = [parents]
            role = cls(name, grants=spec.get('grants', []), parents=parents)

        else:
            role = cls(name, grants=spec)

        return role


class NotAuthorized(RuntimeError):
    pass


class NotDefinedError(Exception):
    pass
