# -*- coding: utf-8 -*-
"""
Copyright 2013-2014 Olivier Cortès <oc@1flow.io>

This file is part of the sparks project.

It provides {python,django}-social-auth pipeline helpers.

As soon as I used them in 2 projets I manage, I moved them
to sparks to mutualize the code.

1flow is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

1flow is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with 1flow.  If not, see http://www.gnu.org/licenses/
"""

import logging

from constance import config

from django.shortcuts import redirect

from social_auth.backends.facebook import FacebookBackend
from social_auth.backends.twitter import TwitterBackend
from social_auth.backends import google


LOGGER = logging.getLogger(__name__)


def get_social_avatar(social_user, user, details, request, response, backend,
                      is_new=False, *args, **kwargs):
    """ Get the user's social avatar and store it in social-auth's DB.

    Current implementation handles facebook, Google (oauth2) and Twitter.

    """

    try:
        url = None

        if isinstance(backend, FacebookBackend):
            if 'id' in response:
                url = u'http://graph.facebook.com/{}/picture?type=large'.format(
                    response['id'])

        elif isinstance(backend, google.GoogleOAuth2Backend):
            url = response.get('picture', None)

        elif isinstance(backend, TwitterBackend):
            url = response.get('profile_image_url', None)

        if url:
            mongo_user = user.mongo

            if mongo_user.avatar_url != url:
                mongo_user.avatar_url = url
                mongo_user.save()

                LOGGER.info(u'Saved new avatar for user %s from backend %s.',
                            user, social_user)

        #     avatar = urlopen(url)
        #     photo = Photo(author=user, is_avatar=True)
        #     photo.picture.save(slugify(user.username+"social") + '.jpg',
        #             ContentFile(avatar.read()))
        #     photo.save()

    except:
        LOGGER.exception(u'Could not get avatar for user %s from '
                         u'backend %s.', user, social_user)


def throttle_new_user_accounts(social_user, user, details, request,
                               response, backend, is_new=False,
                               *args, **kwargs):
    """ Deactivate newly created users if registrations are closed.

    They are also redirected to the ``social_signup_closed`` page to
    inform them about what's going on.

    .. note:: accounts still get created in the database, and we keep them.
        This is intended to be able to contact users if registrations are
        opened again later.
    """

    if is_new and not config.SOCIAL_REGISTRATION_ENABLED:

        user.is_active = False
        user.save()

        LOGGER.warning(u'De-activated new user account %s from backend %s on '
                       u'the fly because social registrations are currently '
                       u'disabled.', user, social_user)

        # Wrap the 'official' account view to signify the user we are closed.
        return redirect('social_signup_closed')
