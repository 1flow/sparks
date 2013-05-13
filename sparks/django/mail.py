# -*- coding: utf8 -*-
"""
    Sparks mail utils.
    Convert Django's mail functions into parallel threaded ones.
    Rassemble the HTML mail message stuff into a convenient function.

    Inspired from:
    - http://djangosnippets.org/snippets/285/
    - http://djangosnippets.org/snippets/2371/
    - https://docs.djangoproject.com/en/1.5/topics/email/#the-emailmessage-class

    .. versionadded:: 1.17
"""

import os
import urlparse
import logging

from bs4 import BeautifulSoup
from email.MIMEImage import MIMEImage

from django.conf import settings
from django.template import loader, Context, Template
from django.core.mail import EmailMultiAlternatives
from django.utils import translation
from django.core.mail import (EmailMessage,
                              send_mail as django_send_mail,
                              mail_admins as django_mail_admins)

from ..foundations.classes import BatcherThread


LOGGER = logging.getLogger(__name__)


def send_mail_html(*a, **kw):
    """ Send mail in a dedicated thread.

    :param attachments: a list or tuple passed as arguments (*args)
        to django's :meth:`~django.core.mail.EmailMessage.attach()`
        method. Example: (fname, fdata, mime),
        where `fname` is a string (the basename of the file, used to
        ease the "save attachment" on the customer mail-client side),
        `fdata` is the content of the file (usually the result of
        `f.read()`), and `mimetype` is a self-explanatory string
        (eg. "application/pdf").

    : param file_attachments: idem, passed as *args to
        :meth:`~django.core.mail.EmailMessage.attach_file()`. In most
        cases, this can be just a tuple like ('filename', ).

        .. versionadded:: 1.17

    """

    parallel         = kw.pop('parallel', True)
    attachments      = kw.pop('attachments', ())
    file_attachments = kw.pop('file_attachments', ())

    mesg = EmailMessage(*a, **kw)

    # Main content is now text/html
    mesg.content_subtype = "html"

    for attachment in attachments:
        mesg.attach(*attachment)

    for file_attachment in file_attachments:
        mesg.attach_file(*file_attachment)

    BatcherThread(mesg.send, parallel=parallel).start()


def send_mail(*args, **kwargs):
    """ Wraps the Django :func:`send_mail` function into a parallel thread
        for immediate reactivity on the web-front side.

        .. versionadded:: 1.17
    """

    parallel = kwargs.pop('parallel', True)
    BatcherThread(django_send_mail, args=args, kwargs=kwargs,
                  parallel=parallel).start()


def mail_admins(*args, **kwargs):
    """ Wraps the Django :func:`mail_admins` function into a parallel thread
        for immediate reactivity on the web-front side.

        .. versionadded:: 1.17
    """

    parallel = kwargs.pop('parallel', True)
    BatcherThread(django_mail_admins, args=args, kwargs=kwargs,
                  parallel=parallel).start()


# •••••••••••••••••••••••••••••••••••••••••••••••••••• HTML Mail with templates


def image_match_tag(tag):
    """ BeautifulSoup4 helper. """
    return (tag.name == u'img' or
            tag.name == u'table' and 'background' in tag)


def handle_embedded_images(msg, html_part):

    def resolve_path(path):
        url_replacements = (
            (settings.STATIC_URL, settings.STATIC_ROOT),
            (settings.MEDIA_URL, settings.MEDIA_ROOT),
        )
        for base_url, base_path in url_replacements:
            if path.startswith(base_url):
                # `base_url` are supposed to end with '/', not `base_path`
                fullpath = os.path.join(base_path, path.replace(base_url, ''))
                return fullpath

        for base_dir in (settings.STATIC_ROOT, settings.MEDIA_ROOT):
            fullpath = os.path.join(base_dir, path)
            if os.path.exists(fullpath):
                return fullpath

        raise LookupError("Could not resolve path '%s'" % path)

    soup = BeautifulSoup(html_part)
    images = []
    added_images = []

    for index, tag in enumerate(soup.findAll(image_match_tag)):
        if tag.name == u'img':
            attribute = 'src'
        else:
            attribute = 'background'

        # If the image was already added, skip it.
        if tag[attribute] in added_images:
            continue

        added_images.append(tag[attribute])
        images.append((tag[attribute], 'img%d' % index))
        tag[attribute] = 'cid:img%d' % index

    html_part = str(soup)

    msg.attach_alternative(html_part, "text/html")

    for filename, file_id in images:
        path = resolve_path(filename)
        with open(path, 'rb') as image_file:
            msg_image = MIMEImage(image_file.read())
            msg_image.add_header('Content-ID', '<%s>' % file_id)
            msg.attach(msg_image)

    return msg


def handle_external_images(msg, html_part):

    soup = BeautifulSoup(html_part, 'html.parser')

    for index, tag in enumerate(soup.findAll(image_match_tag)):
        if tag.name == u'img':
            attribute = 'src'
        else:
            attribute = 'background'

        url = tag[attribute]

        if not url.startswith("http://"):
            url = urlparse.urljoin("http://" + settings.DOMAIN, url)
            tag[attribute] = url

    html_part = str(soup)
    msg.attach_alternative(html_part, "text/html")

    return msg


def send_mail_html_from_template(template, subject, recipients,
                                 sender=None, context=None,
                                 fail_silently=False, force_lang=None,
                                 parallel=True):
    """
    This function will send a multi-part e-mail with both HTML and
    Text parts.

    :param template: the name of the template. Both HTML (.html) and plain
        text (.txt) versions of the template must exist. You can specify
        either the .txt, the .html, or no extension at all, the function

    :param context: should be a dictionary. It is applied on the email
        templates and the subject.

    :param subject: a unicode string, which can contain template tags.

    :param recipients: can be either a string (eg. 'a@b.re') or a list
        (eg. ['a@b.re', 'c@d.re']). Type conversion is done if needed.

    :param sender: unicode string (eg. 'Name <email>') or ``None``. In this
        case Django's ``DEFAULT_FROM_EMAIL`` setting will be used.

    :param parallel: Defaults to ``True``, in which case the sending will
        be done in a parallel thread. In this situation, the return value
        will always be ``True`` because we have no way to known if the
        sending really succeeded or not. If not parallel, this function
        will return the real return value from the ``msg.send()`` method,
        but the operation can block in some situations.

    """

    def attach_html_and_images(msg, html_part):

        if getattr(settings, "MAILER_EMBED_IMAGES", False):
            handler = handle_embedded_images
        else:
            handler = handle_external_images

        return handler(msg, html_part)

    if context is None:
        context = {}

    if sender is None:
        sender = settings.DEFAULT_FROM_EMAIL

    if isinstance(recipients, basestring):
        recipients = [recipients]

    context.update({
        'MEDIA_URL': settings.MEDIA_URL,
        'STATIC_URL': settings.STATIC_URL
    })

    prefix = getattr(settings, "EMAIL_SUBJECT_PREFIX", None)

    if prefix is not None:
        subject = u'[{0}] {1}'.format(prefix, subject)

    stemplate = Template(subject)

    if force_lang is not None:
        current_lang = translation.get_language()
        translation.activate(force_lang)

    subject   = stemplate.render(Context(context))
    text_part = loader.render_to_string('%s.txt' % template, context)
    html_part = loader.render_to_string('%s.html' % template, context)

    if force_lang:
        translation.activate(current_lang)

    msg = EmailMultiAlternatives(subject=subject, body=text_part,
                                 to=recipients, from_email=sender)

    attach_html_and_images(msg, html_part)

    if parallel:
        BatcherThread(target=msg.send, args=(fail_silently, )).start()
        retval = True

    else:
        retval = msg.send(fail_silently)

    return retval
