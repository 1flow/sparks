# -*- coding: utf-8 -*-
""" Django sparks views mixins. """

import json
import logging

from django.http import HttpResponseRedirect

LOGGER = logging.getLogger(__name__)


class ExtraContext(object):

    """ Mixin to add an extra context to a generic-derived view class. """

    extra_context = {}

    def get_context_data(self, **kwargs):
        """ Damned pep257, isn't this completely obvious?!?. """

        context = super(ExtraContext, self).get_context_data(**kwargs)
        context.update(self.extra_context)
        return context


class RedirectOnNextView(object):

    """ A mixin to integrate the ``next`` input field.

    This view overrides the :meth:`post` method and redirects to
    ``next`` if everything is OK.

    .. warning:: untested.
    """

    next_url = None

    def get_context_data(self, *args, **kwargs):
        """ Mein Got, pep257, this is a 3-lines method. """

        context = super(RedirectOnNextView,
                        self).get_context_data(*args, **kwargs)

        if 'next_url' not in context:
            context['next_url'] = self.next_url

        return context

    def post(self, request, *args, **kwargs):
        """ Return an HttpResponseRedirect to ``next`` if is set. """

        result = super(RedirectOnNextView, self).post(request, *args, **kwargs)

        next_url = request.POST.get('next_url', None)

        if next_url is None:
            next_url = self.next_url

        if next_url is None:
            return result

        return HttpResponseRedirect(next_url)


class FilterMixin(object):

    u"""
    View mixin which provides filtering for ListView.

    Injects into the context:

    - `self.filter_url_get_key` to get the full filter string into the template.
    - `self.native_filters` if the attribute exists. It's usually set by the
      :meth:`filter_queryset` method in case of multi-word or multiple query
      methods for some filters (eg. “is:active” and “not:closed” will both
      result in ``self.native_filters['is_active'] = True``).

    https://gist.github.com/robgolding63/4097500
    http://www.robgolding.com/blog/2012/11/17/django-class-based-view-mixins-part-2/
    """

    filter_url_get_key = 'filter'
    default_filter_param = None

    def filter_queryset(self, qs, filter_param):
        """ Just return the queryset. You should override this method. """

        return qs

    def get_filter_param(self):
        """ Still alive, pep257. """

        return self.request.GET.get(self.filter_url_get_key,
                                    self.default_filter_param)

    def get_queryset(self):
        """ You will not get me, pep257. """

        return self.filter_queryset(
            super(FilterMixin, self).get_queryset(),
            self.get_filter_param())

    def get_context_data(self, *args, **kwargs):
        """ Forward the filter parameter in the context. """

        context = super(FilterMixin, self).get_context_data(*args, **kwargs)

        context.update({
            self.filter_url_get_key: self.get_filter_param(),
        })

        if hasattr(self, 'native_filters'):
            context.update({
                'native_filters': self.native_filters
            })

        return context


class SortMixin(object):

    """
    View mixin which provides sorting for ListView.

    https://gist.github.com/robgolding63/4097500
    http://www.robgolding.com/blog/2012/11/17/django-class-based-view-mixins-part-2/

    modified for '-' in front of sort_by param and no 'order' param,
    to be compatible with django-sorting-bootstrap.
    """

    sort_url_get_key = 'sort_by'
    default_sort_param = None

    def sort_queryset(self, qs, sort_by):
        """ Try the most basic sorting possible.

        If :param:`sort_by` is a database field name (eg. "-name"), this
        should just work, and the developper won't need to override this
        method in most cases.
        """

        if sort_by:

            if isinstance(sort_by, str) or isinstance(sort_by, unicode):
                try:
                    qs = qs.order_by(sort_by)

                except:
                    LOGGER.exception(u'Could not sort QuerySet by %s', sort_by)
                    # Most probably, the sort_by needs pre/post-processing
                    # by an overriden method. Too bad we couldn't help.
                    pass

            else:
                try:
                    qs = qs.order_by(*sort_by)

                except:
                    LOGGER.exception(u'Could not sort QuerySet by %s', sort_by)
                    # Most probably, the sort_by needs pre/post-processing
                    # by an overriden method. Too bad we couldn't help.
                    pass

        return qs

    def get_sort_params(self):
        """ Obvious, pep257. """

        return self.request.GET.get(self.sort_url_get_key,
                                    self.default_sort_param)

    def get_queryset(self):
        """ Obvious, pep257. """

        return self.sort_queryset(
            super(SortMixin, self).get_queryset(),
            self.get_sort_params())

    def get_context_data(self, *args, **kwargs):
        """ Forward the sort parameter in the context. """

        context = super(SortMixin, self).get_context_data(*args, **kwargs)

        context.update({
            self.sort_url_get_key: self.get_sort_params(),
        })
        return context


class ListCreateViewMixin(SortMixin, FilterMixin):

    """ Automatically add a list of objects of the main class to context.

    This allows ListCreateViews to get the object_list populated automatically.

    Inspired from http://stackoverflow.com/a/12883683/654755

    You can specify:

    - a :meth:`list_queryset_filter(self, qs)` method, that will
      filter the model queryset exactly how you want.
    - class.list_queryset_filter_user to ``False`` if you do not want to
      filter the QS on the user field, against the self.request.user value.
      This filter is so common (only superusers get all "things") that it
      defaults to ``True``.

    """

    list_queryset_filter_user = True

    def get_context_data(self, **kwargs):
        """ Populate the context with the object list, filtered and sorted.

        The method will honor :attr:`list_queryset_filter_user` and will
        filter with :meth:`list_queryset_filter` if it exists.
        """

        object_list_name = '{0}_list'.format(
            self.model.__name__.lower())

        if object_list_name in kwargs:
            raise RuntimeError(u'Multiple instances of {0} in context!'.format(
                               object_list_name))

        # We build an independant QuerySet; the CreateView part already
        # handles the main one, which with we must not interfere.
        qs = self.model.objects.all()

        # Call the SortMixin & FilterMixin methods on this alternate QS.
        qs = self.sort_queryset(
            self.filter_queryset(
                qs, self.get_filter_param()),
            self.get_sort_params())

        if self.list_queryset_filter_user:
            try:
                qs = qs.filter(user=self.request.user)

            except:
                LOGGER.exception(u'Could not filter %s on user field '
                                 u'against %s', qs, self.request.user)

        try:
            kwargs[object_list_name] = self.list_queryset_filter(qs)

        except AttributeError:
            kwargs[object_list_name] = qs

        return super(ListCreateViewMixin, self).get_context_data(**kwargs)


class OwnerQuerySetMixin(object):

    """ Filter the QuerySet to get only owner's objects.

    In case :attr:`superuser_gets_full_queryset` is ``True``,
    the :meth:`get_queryset` method will honor a special property
    called ``user.is_staff_or_superuser_and_enabled`` (which is
    completely optional). This property is assumed to return a boolean
    value.

    This mechanism is used to allow dynamic filtering in case staff
    members want to disable their permissions temporarily to get a
    standard user interface.
    """

    superuser_gets_full_queryset = False
    ownerqueryset_filter = None

    def get_queryset(self):
        """ Allow only owner to delete its own objects. """

        qs = super(OwnerQuerySetMixin, self).get_queryset()

        if self.superuser_gets_full_queryset:

            user = self.request.user

            try:
                # This is a 1flow specific thing, and
                # will probably fail everywhere else.
                really_full = user.is_staff_or_superuser_and_enabled

            except AttributeError:
                really_full = user.is_superuser

            if really_full:
                return qs

        if self.ownerqueryset_filter:
            kwargs = {self.ownerqueryset_filter: self.request.user}
        else:
            kwargs = {'user': self.request.user}

        return qs.filter(**kwargs)


class DRFLoggerMixin(object):

    u"""
    Allows us to log any incoming request and to know what's in it.

    Usage:

        class VideoViewSet(DRFLoggerMixin,
                   mixins.ListModelMixin,
                   …
                   viewsets.GenericViewSet):
            pass

    References:
        http://stackoverflow.com/a/15579198/654755

    Updates:
        https://gist.github.com/Karmak23/2ea1d62ea32edbeed07b
    """

    def initial(self, request, *args, **kwargs):
        """ Override :meth:`initial` as suggested by Tom Christie. """

        try:
            data = request.DATA

        except:
            data = None

        else:
            try:
                data = json.dumps(data, sort_keys=True, indent=2)

            except:
                pass

            # import re
            # regex = re.compile('^HTTP_')
            # dict((regex.sub('', header), value) for (header, value)
            #        in request.META.items() if header.startswith('HTTP_'))

        LOGGER.info(u'%(method)s request on “%(path)s” for %(user)s '
                    u'from %(origin)s (%(useragent)s):\n'
                    u'auth: %(auth)s, authenticators: [\n%(auths)s\n]\n'
                    u'content-type: %(content)s\n'
                    u'data: %(data)s\n'
                    u'files: {\n    %(files)s\n}' % {
                        'method': request.method,
                        'user': request.user.username,
                        'path': request.get_full_path(),
                        'origin': request.META.get('HTTP_HOST', u'Unknown'),
                        'useragent': request.META.get('HTTP_USER_AGENT',
                                                      u'Unknown'),
                        'auth': request.auth,
                        'auths': u'\n    '.join(
                            unicode(x) for x in request.authenticators),
                        'data': data,
                        'files': u'\n    '.join(
                            u'%s: %s' % (k, v)
                            for k, v in sorted(request.FILES.items())
                        ),
                        'content': request.content_type,
                    }
                    )

        return super(DRFLoggerMixin, self).initial(request, *args, **kwargs)
