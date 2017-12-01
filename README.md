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

Unfortunately, this quickly becomes cumbersome.

### Enter A New Approach: Context-Based Role Resolution
With Autoritah, a user's role is not static but changes based on the context
object - essentially, instead of asking "what is this user's role?", we ask
"what is the user's role given this object?". Once the role is dynamically 
decided, it is very easy to grant or deny permission to perform an action 
without any need of additional assertions. 