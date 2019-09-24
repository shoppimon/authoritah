Authoritah - Framework Agnostic Python RBAC Library
===================================================
Authoritah is a Python RBAC library. It is designed to be framework
agnostic, in the sense that it is not coupled with any Web framework or ORM
library. In addition, Authoritah provides a highly granular role system using
a unique approach of context-based role resolution.

[![Build Status](https://travis-ci.org/shoppimon/authoritah.svg?branch=master)](https://travis-ci.org/shoppimon/authoritah)

## Compatibility 
We test Authoritah on Python 3.5, 3.6, 3.7 and Pypy 3. It is possible that
older versions of Authoritah will work with Python 2.7 as well, but Python 
versions below 3.5 are not supported. 

## Installation
The easiest way to install Authoritah is via pip:

    pip install authoritah 

## Overview & Terminology
The following terms are common in many authorization frameworks, but can have
specific meaning in *authoritah* so it is important to clarify them first:

### Identities
In simple terms, an identity is a user - an entity using the system (be it a
person, a machine authenticating with an API key, a default "anonymous" user,
etc.) Identities can have **roles** - in *authoritah*, an identity's roles are
usually in relation to a given **context object**, although identities can have
default roles as well.

In *authoritah* you are not expected to use a specific structure for identity
objects - they are opaque as far as the library is concerned, and are only
passed around between different callables you provide.

### Roles
A role is given to an identity, and defines a set of **permissions** - actions
that the user is allowed to perform on an object or in the system.

An identity can have more than one role (for example a user may be both a
**hiring_manager** and a **content_editor**).  In addition, roles can inherit
permissions from one or more other roles (for example, a **content_editor** can
inherit from **content_viewer**).

Unlike many other authorization frameworks, in *authoritah* roles are not
global (although they can be), but are derived from context - for example a
user may be a **content_editor** for all articles, or may be a
**content_editor** only for the articles they created, and **content_viewer**
for all other articles.

### Permissions
Permissions, simply put, are "rights granted to a given identity based on its
roles". For example, someone with a **content_editor** role have the
**article_edit**, **article_publish** and **article_unpublish** permissions.

Implementing authorization checks in a system normally involves checking
whether the user has one or more permissions granted to them before proceeding
with an action.

### Strict Mode:
The Authorizer class may be instantiated with strict=True (defaults to False).

Strict mode can raise exceptions in two cases:

* If is_allowed is called for a permission not defined in any of the roles defined.
* If a role in the identity provided to is_allowed is not defined

This is useful to check if one forgot to add a role or permission.


### Context Objects
The **context object** is the object on which the operation is performed. For
example, when editing an article the context object is the article. As
mentioned, in *authoritah* context objects have a more central role than
with many other authorization frameworks - they are taken into account when
deciding the user's role.

## Quick Start
The following is a quick start guide to applying authorization to your code
using *authoritah*.

We'll follow an example of an imaginary, simplified content management system
with 3 objects: articles, comments and users.

### 1. Define Roles and Permissions
As with any RBAC system, it is recommended to start with defining some roles
and what permissions they grant. With *Authoritah*, it is recommended to think
of roles in relation to objects in the system.

You can define your roles and permissions in a configuration file - a `YAML` or
`JSON`, or even a Python `dict`:

```YAML
  ---
  viewer:
    - article_list
    - article_view
    - comment_list
    - comment_view
    - user_create

  user:
    parents: [ 'viewer' ]
    grants:
      - comment_create
      - comment_upvote

  contributor:
    parents: [ 'user' ]
    grants:
      - article_create

  content_admin:
    - comment_edit
    - comment_delete
    - article_edit
    - article_delete

  user_admin:
    - user_edit
    - user_delete

  super_admin:
    parents:
      - contributor
      - content_admin
      - user_admin
```

Some things to notice:
* Each `role` is designated by a unique key (or name), and defines,
  optionally, a list of permissions (`grants`).
* Roles can inherit permissions from other roles. This is done by providing
  a list of inherited roles as `parents`.
* As a shortcut, you can define a role by simply providing the list of
  permissions it grants, skipping the `grants` key. This format works nicely
  for roles not inheriting from any other role.

Most importantly, roles are defined in a very granular way following an
approach of least possible access. The right way to think of permissions in
*authoritah* is to consider whether someone with the given role should have
a given permission **under all circumstances** or only in specific contexts.

In our example, a `contributor` can create any article, but cannot delete
any article - only their own articles. Later, we will see how to use dynamic
role resolution to elevate a specific user to `content_admin` for specific
contexts, so they can edit and delete their own articles.

### 2. Initialize an Authorizer and hook in identity management
Everything you will do with *authoritah* begins with creating an an
`Authorizer` object. Assuming we read our roles & permissions configuration
from a YAML file named `authorization.yml`, here is how this is done:

```python
import yaml
from authoritah import Authorizer

with open('authorization.yml') as f:
    roles = yaml.safe_load(f)

authz = Authorizer(permissions=roles)
```

Since *authoritah* is not bound to any authentication or identity
management implementation, you will need to tell your Authorizer how to get
an identity object, and how to get a list of roles from this object.

The simplest way to do this would be to use two decorator methods of the
`Authorizer` object we just created: `authz.identity_provider` and
`authz.default_role_provider`:

```python
@authz.identity_provider
def get_current_user(request):
    """This function returns the current authenticated user object
    """
    return request.user


@authz.default_role_provider
def get_user_roles(user, context=None):
    """Get roles for the current user.

    This function should always accept an identity object (as returned
    by the defined identity provider) and return either a list of roles,
    a string representing a single role, or None for a user with no roles.

    Note that this function also receives the current context object. It
    may be used, if needed, to infer roles - but this is usually not
    recommended.
    """
    return user.roles
```

In most cases these two functions should be very simple - they are just "glue"
that integrates your existing code with *authoritah*.

### 3. Define Context-Specific Role Resolution
If your system does not require any dynamic role resolution (e.g. permissions
are global and are not related to context objects in your case), you can skip
this phase and use *authoritah* like you would use any other RBAC library.

However, in most cases you would like to give users additional roles based on
the object they are accessing - the context object.

This is done using the `authz.context_role_provider` decorator. This decorator
should be used to decorate classes, specifying how we should get the roles when
the context object is of a certain type.

Assume that our CRM has an ORM or entity class that represents an article:
 ```python
class Article:

    title = None
    content = None
    created_by = None
```

You can now use a decorator to tell Authoritah that `article_user_roles` is the
role provider for objects of type `Article`, or any subtype of it:
```python
@authz.role_provider(Article)
def article_user_roles(user, article):
    if user.id == article.created_by:
        return ['content_admin']
    return []
```

Thus, we have told our authorizer to call `article_user_roles` whenever the 
context object is an `Article` object. The list of roles returned by this
callable will be appended to the list of existing global roles the user already
has. This way, we know that if the user is the creator of the article, they
should get permissions as if they have the `content_admin` role (meaning they
can edit or delete *this specific article*).

Another way of doing this will be to use the `class_role_provider` annotation 
on the context object class, providing it a method name on the same class to
use as a context role provider:
 ```python
@authz.class_role_provider('user_roles')
class ProtectedArticle(Article):

    def user_roles(self, user):
        if user.id == self.created_by:
            return ['content_admin']
        return []
```

Note that this case will work only for objects of `ProtectedArticle`, not the 
original `Article` base class. However, it *will* work for any class inheriting
from `ProtectedArticle`. 

### 4. Apply Authorization Checks in Your Code
Last but very important, start checking for permissions before you perform
some operations in your code.

There are two common ways to do this. One is explicit:
```python
def modify_article(article_id, data):
    """Assume this is your Web framework's handler for article editing
    """
    article = DB.article.get(article_id)
    if not authz.is_allowed('article_edit', article):
        return 'You are not allowed to edit this article', 403

    # ... proceed to update the article
```
The other is using a decorator, which works well for object methods where the
object is our context object. Let's update our class definition from before:

```python
@authz.class_role_provider('user_roles')
class ProtectedArticle(Article):

    @authz.require('article_edit')
    def modify(self, new_data):
        # ... proceed to modify my own attributes
        pass
        
    def user_roles(self, user):
        if user.id == self.created_by:
            return ['content_admin']
        return []
```

In the example above, if the user doesn't have the `article_edit` permission,
calling `modify()` will raise an `authoritah.NotAuthorized` exception, which
you will then need to catch and handle.

## Background: Why Context-Based Role Resolution?
In most RBAC / ACL frameworks, each user is given one or more pre-defined
roles, which in turn decide their permissions to perform operations on various
objects. This works well in many cases, but falls short when static permissions
are not enough to decide whether a user should be allowed to perform an
operation.

For example, in a content management system a user may be have an "editor" role
granting them permission to edit articles. This works well in a "flat" system
where all editors can edit all articles.

But what if we want users to only be able to edit articles that they created?
Or what if we want users to be able to designate specific editors for an
article? Granting a global "editor" role here is just not enough.

### Existing Solutions: Post-Hoc Assertions
Most current RBAC libraries tackle this problem by adding dynamic assertion
capabilities on top of static roles and permissions. They allow developers to
specify additional assertion callables per granted permission. Once a user is
granted permission to take an action based on their role, additional
assertions are executed, essentially checking if the permission should still
be granted, given the user and a context object (in our example the article
being edited).

Unfortunately, this has a few major drawbacks:
* Writing custom assertions quickly becomes cumbersome as permissions become
  more granular and the number of permissions in the system grows.
* This model forces an approach of granting roles with the maximal permissions.
  Narrowing down permissions to only apply in specific contexts is an
  afterthought.

### Enter A New Approach: Context-Based Role Resolution
With *authoritah*, a user's role is not static but changes based on the context
object. Essentially, instead of asking "what is this user's role?", we ask
"what is the user's role given this object?". Once the role is dynamically
decided, it is very easy to grant or deny permission to perform an action
without any need of additional assertions.

In addition, it advocates a process where minimal permissions are granted
through each role initially. In the right context, a user may have additional
permissions through additional roles assigned to them.

This, in our opinion, reduces the risk of permissions leakage as it encourages
a more granular and limited approach to granting permissions.

# License
Copyright (c) 2017 Shoppimon LTD

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
