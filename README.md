Authoritah - Framework Agnostic Python RBAC Library
===================================================
Authoritah is a Python 2.7 / 3.6 RBAC library. It is designed to be framework 
agnostic, in the sense that it is not coupled with any Web framework or ORM
library. In addition, Authoritah provides a highly granular role system using 
a unique approach of context-based role resolution. 

[![Build Status](https://travis-ci.org/shoppimon/authoritah.svg?branch=master)](https://travis-ci.org/shoppimon/authoritah)

## Terminology
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

Unlike many other authorization frameworks, in **authoritah** roles are not
global (although they can be), but are derived from context - for example a 
user may be a **content_editor** for all articles, or may be a 
**content_editor** only for the articles they created, and **content__viewer**
for all other articles. 

### Permissions
Permissions, simply put, are "rights granted to a given identity based on it's
roles". For example, someone with a **content_editor** role have the 
**article_edit**, **article_publish** and **article_unpublish** permissions.

Implementing authorization checks in a system normally involves checking 
whether the user has one or more permissions granted to them before proceeding
with an action.

### Context Objects
The **context object** is the object on which the operation is performed. For
example, when editing an article the context object is the article. As 
mentioned, in **authoritah** context objects have a more central role than
with many other authorization frameworks - they are taken into account when
deciding the user's role.

## Quick Start
The following is a quick start guide to applying authorization to your code
using *authoritah*.

We'll follow an example of an imaginay, simplified content management system
with 3 objects: articles, comments and users.

#### 1. Define Roles and Permissions
As with any RBAC system, it is recommended to start with defining some roles
and what permissions they grant. With *Authoritah*, it is recommended to think
of roles in relation to objects in the system.

You can define your roles and permissions in a configuration file - a `YAML` or
`JSON`, or even a Python `dict`:

    roles:
      viewer:
        - article_list
        - article_view
        - comment_list
        - comment_view
        - user_create
      
      user:
        inherits: [ 'viewer' ]
        grants:
          - comment_create
          - comment_upvote
      
      contributor:
        inherits: [ 'user' ]
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
      
      root:
        inherits: 
          - contributor
          - content_admin
          - user_admin

Some things to notice: 
* Each `role` is desitgnated by a unique key (or name), and defines, 
  optionally, a list of permissions (`grants`). 
* Roles can inherit permissions from other roles
* As a shortcut, you can define a role by simply providing the list of 
  permissions it grants, skipping the `grants` key. This format works 
  nicely for roles not inheriting from any other role.

Most importantly, roles are defined in a very granular way following an
approach of least possible access. The right way to think of permissions in 
*authoritah* is to consider whether someone with the given role should have
a given permission **under any circumstances** or only in specific contexts.

In our example, a `contributor` can create any article, but cannot delete
any article - only their own articles. Later, we will see how to use dynamic
role resolution to elevate a specific user to `content_admin` for specific
contexts, so they can edit and delete their own articles. 

#### 2. Initialize an Authorizer and hook in identity management

#### 3. Define Context-Specific Role Resolution

#### 4. Apply Authorization Checks in Your Code


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
* This model forces an aproach of granting roles with the maximal permissions.
  Narrowing down permissions to only apply in specific contexts is an 
  afterthought.

### Enter A New Approach: Context-Based Role Resolution
With Autoritah, a user's role is not static but changes based on the context
object - essentially, instead of asking "what is this user's role?", we ask
"what is the user's role given this object?". Once the role is dynamically 
decided, it is very easy to grant or deny permission to perform an action 
without any need of additional assertions. 

In addition, it advocates a process where minimal permissions are granted 
through each role initially. In the right context, a user may have additional
permissions through additional roles assigned to them. 

This, in our opinion, reduces the risk of permissions leakage.
