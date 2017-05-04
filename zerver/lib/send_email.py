from django.conf import settings
from django.core.mail import send_mail
from django.template import loader, TemplateDoesNotExist
from django.utils.timezone import now as timezone_now
from zerver.models import UserProfile, ScheduledJob, get_user_profile_by_email

import datetime
import ujson

from typing import Any, Dict, Iterable, List, Optional, Text

def display_email(user):
    # type: (UserProfile) -> Text
    # Change to '%s <%s>' % (user.full_name, user.email) once
    # https://github.com/zulip/zulip/issues/4676 is resolved
    return user.email

def send_email(template_prefix, to_email, from_email=None, context={}):
    # type: (str, Text, Optional[Text], Dict[str, Any]) -> bool
    subject = loader.render_to_string(template_prefix + '.subject', context).strip()
    message = loader.render_to_string(template_prefix + '.txt', context)
    # Remove try/expect once https://github.com/zulip/zulip/issues/4691 is resolved.
    try:
        html_message = loader.render_to_string(template_prefix + '.html', context)
    except TemplateDoesNotExist:
        html_message = None
    if from_email is None:
        from_email = settings.NOREPLY_EMAIL_ADDRESS
    return send_mail(subject, message, from_email, [to_email], html_message=html_message) > 0

def send_email_to_user(template_prefix, user, from_email=None, context={}):
    # type: (str, UserProfile, Optional[Text], Dict[str, Text]) -> bool
    return send_email(template_prefix, display_email(user), from_email=from_email, context=context)

def send_future_email(template_prefix, recipients, from_email=None, context={},
                      delay=datetime.timedelta(0), tags=[]):
    # type: (str, List[Dict[str, Any]], Optional[Text], Dict[str, Any], datetime.timedelta, Iterable[Text]) -> None
    subject = loader.render_to_string(template_prefix + '.subject', context).strip()
    email_text = loader.render_to_string(template_prefix + '.txt', context)
    email_html = loader.render_to_string(template_prefix + '.html', context)

    if from_email is None:
        from_email = settings.NOREPLY_EMAIL_ADDRESS
    for recipient in recipients:
        email_fields = {'email_html': email_html,
                        'email_subject': subject,
                        'email_text': email_text,
                        'recipient_email': recipient.get('email'),
                        'recipient_name': recipient.get('name'),
                        'from_email': from_email}
        ScheduledJob.objects.create(type=ScheduledJob.EMAIL, filter_string=recipient.get('email'),
                                    data=ujson.dumps(email_fields),
                                    scheduled_timestamp=timezone_now() + delay)
