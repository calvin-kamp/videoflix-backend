"""Background jobs of the auth app, executed by the RQ worker."""

from email.message import MIMEPart
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

# Logo referenced as ``cid:videoflix-logo`` in the MJML templates. It is sent
# inline, because mail clients block remote images and do not render SVG.
LOGO_PATH = Path(__file__).resolve().parent / "static" / "app_auth" / "emails" / "logo.png"
LOGO_CID = "videoflix-logo"


def build_inline_logo():
    """Return the logo as an inline image part with a Content-ID."""
    logo = MIMEPart()
    logo.set_content(
        LOGO_PATH.read_bytes(),
        maintype="image",
        subtype="png",
        disposition="inline",
        filename="logo.png",
        cid=f"<{LOGO_CID}>",
    )

    return logo


def send_templated_email(subject, template_name, context, recipient):
    """Render an email template and send it as HTML with a plain-text part.

    The HTML lives in ``app_auth/templates/emails/html/`` and is compiled
    from the MJML sources in ``app_auth/templates/emails/mjml/``. The plain-
    text part comes from ``app_auth/templates/emails/text/``.

    Args:
        subject: Subject line of the email.
        template_name: File name without extension, e.g. ``"activation"``.
        context: Template context; must only contain serializable values.
        recipient: Email address of the receiver.
    """
    text_body = render_to_string(f"emails/text/{template_name}.txt", context)
    html_body = render_to_string(f"emails/html/{template_name}.html", context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    message.attach_alternative(html_body, "text/html")
    message.attach(build_inline_logo())
    message.send()
