# -*- coding: utf-8 -*-
u""" Django Filters additions.


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
from django.db.models import Q
import django_filters


class M2MListFilter(django_filters.Filter):

    """ A filter that can span across M2M relationships with =1,2,3 syntax. """

    def __init__(self, filter_value=lambda x: x, **kwargs):
        """ Pep257, would you please stop bugging me about inits. """
        super(M2MListFilter, self).__init__(**kwargs)
        self.filter_value_fn = filter_value

    def sanitize(self, value_list):
        """ Return only non-empty values. """
        return [v for v in value_list if v != u'']

    def filter(self, qs, value):
        """ Filter the QS. """

        values = self.sanitize(value.split(u","))

        if not values:
            return qs

        values = map(self.filter_value_fn, values)

        f = Q()

        for v in values:
            kwargs = {self.name: v}
            f |= Q(**kwargs)

        return qs.filter(f).distinct()
