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

    """
    View mixin which provides filtering for ListView.

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
            try:
                qs = qs.order_by(sort_by)

            except:
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
    """

    def get_context_data(self, **kwargs):
        """ Populate the context with the object list, filtered and sorted. """

        object_list_name = '{0}_list'.format(
            self.model.__name__.lower())

        if object_list_name in kwargs:
            raise RuntimeError(u'Multiple instances of {0} in context!'.format(
                               object_list_name))

        user = self.request.user

        # We build an independant QuerySet; the CreateView part already
        # handles the main one, which with we must not interfere.
        qs = self.model.objects.all()

        qs.filter(user=user)

        # Call the SortMixin & FilterMixin methods on this alternate QS.
        qs = self.sort_queryset(
            self.filter_queryset(
                qs, self.get_filter_param()),
            self.get_sort_params())

        kwargs[object_list_name] = qs

        return super(ListCreateViewMixin, self).get_context_data(**kwargs)


class DRFLoggerMixin(object):

    """
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
            LOGGER.exception('Exception while getting request.DATA')

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
