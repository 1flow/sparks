# -*- coding: utf-8 -*-
"""
Sparks helpers, functions and classes for the Django admin.

.. note:: this module will need to import django settings.
    Make sure it is available and set before importing.

.. versionadded:: 1.17
"""


from django.db import transaction
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.filters import SimpleListFilter
from django.template.response import TemplateResponse
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.utils.html import escape

from django.utils.translation import ugettext, ugettext_lazy as _
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.csrf import csrf_protect

from .forms import EmailUserChangeForm, EmailUserCreationForm

csrf_protect_m = method_decorator(csrf_protect)


class UserAdmin(admin.ModelAdmin):

    """ Mimic the standard UserAdmin, as seen in Django 1.5.

    At: https://raw.github.com/django/django/master/django/contrib/auth/admin.py

    We add it in case you would like to include oneflow.base in other apps.
    """

    add_form_template = 'admin/auth/user/add_form.html'
    change_user_password_template = None
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', )}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2')}),
    )
    form = EmailUserChangeForm
    add_form = EmailUserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('first_name', 'last_name', 'email')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions', )

    def get_fieldsets(self, request, obj=None):
        """ Hello my pep257 love. """

        if not obj:
            return self.add_fieldsets
        return super(UserAdmin, self).get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """ Use special form during user creation. """

        defaults = {}
        if obj is None:
            defaults.update({
                'form': self.add_form,
                'fields': admin.util.flatten_fieldsets(self.add_fieldsets),
            })
        defaults.update(kwargs)
        return super(UserAdmin, self).get_form(request, obj, **defaults)

    def get_urls(self):
        """ Hello my pep257 love. """

        from django.conf.urls import patterns
        return patterns('',
                        (r'^(\d+)/password/$',
                         self.admin_site.admin_view(self.user_change_password))
                        ) + super(UserAdmin, self).get_urls()

    def lookup_allowed(self, lookup, value):
        """ Hello my pep257 love. """

        # See #20078: we don't want to allow any lookups involving passwords.
        if lookup.startswith('password'):
            return False
        return super(UserAdmin, self).lookup_allowed(lookup, value)

    @sensitive_post_parameters()
    @csrf_protect_m
    @transaction.commit_on_success
    def add_view(self, request, form_url='', extra_context=None):
        """ Check user permissions. """

        # It's an error for a user to have add permission but NOT change
        # permission for users. If we allowed such users to add users, they
        # could create superusers, which would mean they would essentially have
        # the permission to change users. To avoid the problem entirely, we
        # disallow users from adding users if they don't have change
        # permission.
        if not self.has_change_permission(request):
            if self.has_add_permission(request) and settings.DEBUG:
                # Raise Http404 in debug mode so that the user gets a helpful
                # error message.
                raise Http404(
                    'Your user does not have the "Change user" permission. In '
                    'order to add users, Django requires that your user '
                    'account have both the "Add user" and "Change user" '
                    'permissions set.')

            raise PermissionDenied

        if extra_context is None:
            extra_context = {}

        username_field = self.model._meta.get_field(self.model.USERNAME_FIELD)
        defaults = {
            'auto_populated_fields': (),
            'username_help_text': username_field.help_text,
        }

        extra_context.update(defaults)

        return super(UserAdmin, self).add_view(request, form_url,
                                               extra_context)

    @sensitive_post_parameters()
    def user_change_password(self, request, id, form_url=''):
        """ Change password template . """

        if not self.has_change_permission(request):
            raise PermissionDenied

        user = get_object_or_404(self.queryset(request), pk=id)

        if request.method == 'POST':
            form = self.change_password_form(user, request.POST)

            if form.is_valid():
                form.save()
                msg = ugettext('Password changed successfully.')
                messages.success(request, msg)

                return HttpResponseRedirect('..')
        else:
            form = self.change_password_form(user)

        fieldsets = [(None, {'fields': list(form.base_fields)})]
        adminForm = admin.helpers.AdminForm(form, fieldsets, {})

        context = {
            'title': _('Change password: %s') % escape(user.get_username()),
            'adminForm': adminForm,
            'form_url': form_url,
            'form': form,
            'is_popup': '_popup' in request.REQUEST,
            'add': True,
            'change': False,
            'has_delete_permission': False,
            'has_change_permission': True,
            'has_absolute_url': False,
            'opts': self.model._meta,
            'original': user,
            'save_as': False,
            'show_save': True,
        }

        return TemplateResponse(request,
                                self.change_user_password_template or
                                'admin/auth/user/change_password.html',
                                context, current_app=self.admin_site.name)

    def response_add(self, request, obj, post_url_continue=None):
        """ Determine the HttpResponse for the add_view stage.

        It mostly defers to its superclass implementation but is customized
        because the User model has a slightly different workflow.
        """
        # We should allow further modification of the user just added i.e. the
        # 'Save' button should behave like the 'Save and continue editing'
        # button except in two scenarios:
        # * The user has pressed the 'Save and add another' button
        # * We are adding a user in a popup
        if '_addanother' not in request.POST and '_popup' not in request.POST:
            request.POST['_continue'] = 1

        return super(UserAdmin, self).response_add(request, obj,
                                                   post_url_continue)


class NullFilterSpec(SimpleListFilter):

    """ Thanks http://stackoverflow.com/a/9593302/654755 . """

    title = u''
    parameter_name = u''
    is_charfield = False

    def lookups(self, request, model_admin):

        return (
            ('1', _('Has value'), ),
            ('0', _('None'), ),
        )

    def queryset(self, request, queryset):

        kwargs = {
            self.parameter_name: u'' if self.is_charfield else None,
        }

        if self.value() == '0':
            return queryset.filter(**kwargs)

        if self.value() == '1':
            return queryset.exclude(**kwargs)

        return queryset
