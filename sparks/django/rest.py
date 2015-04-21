# -*- coding: utf-8 -*-
u""" Django REST Framework permissions, signals, utils.


.. Copyright 2015 Olivier Cortès <oc@1flow.io>.

    This file is part of the sparks project.

    sparks is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of
    the License, or (at your option) any later version.

    sparks is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public
    License along with sparks. If not, see http://www.gnu.org/licenses/
"""

import logging

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save

from rest_framework import permissions
from rest_framework.authtoken.models import Token

LOGGER = logging.getLogger(__name__)


# ———————————————————————————————————————————————————————————————————— IsAdmin*


class AdminReadOnly(permissions.BasePermission):

    """ R/O to superusers / staff members, nothing to others. """

    def has_permission(self, request, view):

        user = request.user

        if request.method in permissions.SAFE_METHODS:
            if user.is_superuser or user.is_staff:
                return True

        return False


class IsAdminOrAuthenticatedReadOnly(permissions.BasePermission):

    """ R/W to superusers / staff members, R/O to logged in users. """

    def has_permission(self, request, view):

        user = request.user

        if request.method in permissions.SAFE_METHODS:
            if user.is_authenticated():
                return True

        if user.is_superuser or user.is_staff:
            return True

        return False


class IsAdminOrReadOnly(permissions.BasePermission):

    """ R/W to superusers / staff members, R/O to others. """

    def has_permission(self, request, view):

        user = request.user

        if request.method in permissions.SAFE_METHODS:
            return True

        if user.is_superuser or user.is_staff:
            return True

        return False


# ———————————————————————————————————————————————————————————————————— IsOwner*


class IsOwner(permissions.DjangoObjectPermissions):

    """ R/W to owner, nothing to any other.

    To determine ownership, this class assumes the model instance has either
    a `.user`, a `.owner` or a `.creator` attribute (in this order), all of
    them needing to be FKs to :func:`get_user_model`.

    if the object has no ownership attribute, permission is denied.

    .. note:: for performance reasons and to avoid a DB query, only ``_id``
        fields are compared. Eg. `instance.user` is not accessed, but
        `instance.user_id` instead.
    """

    def has_object_permission(self, request, view, obj):

        for attr_name in ('user_id', 'owner_id', 'creator_id', ):
            try:
                return getattr(obj, attr_name) == request.user.id

            except AttributeError:
                pass

        return False


class IsOwnerOrAdminReadOnly(IsOwner):

    """ R/W to owner, R/O to superusers / staff members, nothing to others.

    .. note:: see :class:`IsOwner` for ownership determination.
    """

    def has_object_permission(self, request, view, obj):

        user = request.user

        if request.method in permissions.SAFE_METHODS:
            if user.is_superuser or user.is_staff:
                return True

        return IsOwner.has_object_permission(self, request, view, obj)


class IsOwnerOrAuthenticatedReadOnly(IsOwner):

    """ R/W to owner, R/O to any logged in user, nothing to others.

    .. note:: see :class:`IsOwner` for ownership determination.
    """

    def has_object_permission(self, request, view, obj):

        if request.method in permissions.SAFE_METHODS:
            if request.user.is_authenticated():
                return True

        return IsOwner.has_object_permission(self, request, view, obj)


class IsOwnerOrReadOnly(IsOwner):

    """ R/W to owner, R/O to any other.

    .. note:: see :class:`IsOwner` for ownership determination.
    """

    def has_object_permission(self, request, view, obj):

        if request.method in permissions.SAFE_METHODS:
            return True

        return IsOwner.has_object_permission(self, request, view, obj)


class IsOwnerOrAdmin(IsOwner):

    """ R/W to owner, superusers and staff members. Nothing to others.

    .. note:: see :class:`IsOwner` for ownership determination.
    """

    def has_object_permission(self, request, view, obj):

        if request.user.is_superuser or request.user.is_staff:
            return True

        return IsOwner.has_object_permission(self, request, view, obj)


class IsOwnerOrAdminOrAuthenticatedReadOnly(IsOwnerOrAdmin):

    """ R/W to owner / superusers / staff, R/O to logged in users.

    .. note:: see :class:`IsOwner` for ownership determination.
    """

    def has_object_permission(self, request, view, obj):

        if request.method in permissions.SAFE_METHODS:
            if request.user.is_authenticated():
                return True

        return IsOwnerOrAdmin.has_object_permission(self, request, view, obj)


class IsOwnerOrAdminOrReadOnly(IsOwnerOrAdmin):

    """ R/W to owner, superusers and staff members ; R/O to others.

    .. note:: see :class:`IsOwner` for ownership determination.
    """

    def has_object_permission(self, request, view, obj):

        if request.method in permissions.SAFE_METHODS:
            return True

        return IsOwnerOrAdmin.has_object_permission(self, request, view, obj)


# ————————————————————————————————————————————————————————————————————— IsSelf*


class IsSelf(permissions.DjangoObjectPermissions):

    """ Grant permission only if the current instance is the request user.

    Used to allow users to edit their own account, nothing to others (even
    superusers).
    """

    def has_object_permission(self, request, view, obj):
        return obj.id == request.user.id


class IsSelfOrReadOnly(permissions.DjangoObjectPermissions):

    """ Grant permissions if instance *IS* the request user, or read-only.

    Used to allow users to edit their own account, and others to read.
    """

    def has_object_permission(self, request, view, obj):

        if request.method in permissions.SAFE_METHODS:
            return True

        return obj.id == request.user.id


class IsSelfOrAdmin(permissions.DjangoObjectPermissions):

    """ Grant R/W to self and superusers/staff members. Deny others. """

    def has_object_permission(self, request, view, obj):

        user = request.user

        if user.is_superuser or user.is_staff:
            return True

        return obj.id == request.user.id


class IsSelfOrAdminOrReadOnly(permissions.DjangoObjectPermissions):

    """ Grant R/W to self and superusers/staff members, R/O to others. """

    def has_object_permission(self, request, view, obj):

        user = request.user

        if request.method in permissions.SAFE_METHODS:
            return True

        if user.is_superuser or user.is_staff:
            return True

        return obj.id == request.user.id


class IsAuthenticatedReadOnly(permissions.BasePermission):

    """ R/O to authenticated users. """

    def has_permission(self, request, view):

        user = request.user

        if request.method in permissions.SAFE_METHODS:
            if user.is_authenticated():
                return True

        return False


# ——————————————————————————————————————————————————————————— Signals receivers


def create_drf_auth_token(sender, instance, created, **kwargs):
    """ Create a DRF Authentication token on user creation.

    Usage:
        # The one-liner wrapper:
        connect_create_drf_auth_token_to_user_post_save()

        # OR manually:

        from django.contrib.auth import get_user_model
        from django.db.models.signals import post_save
        post_save.connect(create_drf_auth_token, sender=get_user_model())
    """

    # from django.dispatch import receiver

    if created:
        Token.objects.create(user=instance)


def connect_create_drf_auth_token_to_user_post_save(UserClass=None):
    """ Wrap the signal connection on demand.

    :param UserClass: your User model class, or Django's one or ``None``.
        If ``None``, :func:`get_user_model` will be run.
    :type UserClass: a :class:`~django.contrib.auth.models.AbstractBaseUser`
        derived class, or None.

    :returns: nothing.
    :raises: nothing.
    """

    post_save.connect(create_drf_auth_token,
                      sender=UserClass or get_user_model())
