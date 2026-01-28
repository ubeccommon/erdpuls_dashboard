"""
Erdpuls Collective Threshold Model - Email Utilities

Features:
- Generic email sending via SMTP
- Contribution confirmation emails (trilingual)
- Password reset emails (trilingual)

© 2026 Michel Garand | Lizenz: CC BY-NC-SA 4.0 | https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from decimal import Decimal

from .config import get_settings

logger = logging.getLogger(__name__)


def send_email(
    to_email: str,
    subject: str,
    html_content: Optional[str],
    text_content: Optional[str] = None
) -> bool:
    """
    Send an email using SMTP settings from config.
    Returns True if successful, False otherwise.
    """
    settings = get_settings()  # Load settings at call time
    
    logger.info(f"Attempting to send email to {to_email}")
    logger.info(f"SMTP config: host={settings.smtp_host}, port={settings.smtp_port}, user={settings.smtp_user}")
    
    if not settings.smtp_host or not settings.smtp_user:
        logger.warning("SMTP not configured, skipping email send")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        msg['To'] = to_email
        
        # Add text and HTML parts
        if text_content:
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        if html_content:
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        # Connect and send
        # Port 465 uses implicit SSL (SMTP_SSL)
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as server:
                if settings.smtp_user and settings.smtp_password:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        else:
            # Port 587 uses STARTTLS
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                if settings.smtp_user and settings.smtp_password:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def send_contribution_confirmation(
    to_email: str,
    to_name: Optional[str],
    offering_title: str,
    offering_id: str,
    contribution_data: dict,
    lang: str = 'en'
) -> bool:
    """
    Send a contribution confirmation/thank you email.
    """
    settings = get_settings()  # Load settings at call time
    base_url = settings.base_url
    
    # Build contribution summary
    items = []
    if contribution_data.get('euro'):
        items.append(f"EUR {contribution_data['euro']:.2f}")
    if contribution_data.get('tokens'):
        items.append(f"{contribution_data['tokens']:.0f} UBECrc (approx. EUR {contribution_data.get('tokens_eur', 0):.2f})")
    if contribution_data.get('hours'):
        category = contribution_data.get('hours_category', '').replace('_', ' ').title()
        items.append(f"{contribution_data['hours']:.1f}h {category} (approx. EUR {contribution_data.get('hours_eur', 0):.2f})")
    
    total = float(contribution_data.get('total_eur', 0))
    contribution_summary = " + ".join(items) if items else f"EUR {total:.2f}"
    
    # Localized content
    if lang == 'de':
        subject = f"Danke für Ihren Beitrag - {offering_title}"
        greeting = f"Liebe/r {to_name}," if to_name else "Hallo,"
        thank_you = "Vielen Dank für Ihren Beitrag zum kollektiven Topf!"
        your_contribution = "Ihr Beitrag"
        total_label = "Gesamtwert"
        privacy_note = "Zur Erinnerung: Öffentlich werden nur Gesamtsummen angezeigt, niemals einzelne Beiträge."
        next_steps = "Nächste Schritte"
        next_steps_text = """
            <li>Wir benachrichtigen Sie, sobald die Schwelle erreicht ist</li>
            <li>Bei Stundenbeiträgen kontaktieren wir Sie zur Koordination</li>
            <li>Das Angebot findet statt, wenn die Gemeinschaft es gemeinsam trägt</li>
        """
        view_offering = "Angebot ansehen"
        closing = "Gemeinsam wachsen, gemeinsam lernen, gemeinsam regenerieren."
        signature = "Das Erdpuls Müllrose Team"
    elif lang == 'pl':
        subject = f"Dziękujemy za Twój wkład - {offering_title}"
        greeting = f"Drogi/a {to_name}," if to_name else "Cześć,"
        thank_you = "Dziękujemy za Twój wkład do wspólnego funduszu!"
        your_contribution = "Twój wkład"
        total_label = "Łączna wartość"
        privacy_note = "Przypomnienie: publicznie wyświetlane są tylko sumy, nigdy indywidualne wkłady."
        next_steps = "Następne kroki"
        next_steps_text = """
            <li>Powiadomimy Cię, gdy próg zostanie osiągnięty</li>
            <li>W przypadku wkładów godzinowych skontaktujemy się w sprawie koordynacji</li>
            <li>Oferta odbędzie się, gdy społeczność wspólnie ją wesprze</li>
        """
        view_offering = "Zobacz ofertę"
        closing = "Wspólnie rośniemy, wspólnie się uczymy, wspólnie regenerujemy."
        signature = "Zespół Erdpuls Müllrose"
    else:
        subject = f"Thank you for your contribution - {offering_title}"
        greeting = f"Dear {to_name}," if to_name else "Hello,"
        thank_you = "Thank you for your contribution to the collective pot!"
        your_contribution = "Your contribution"
        total_label = "Total value"
        privacy_note = "Remember: only totals are displayed publicly, never individual contributions."
        next_steps = "Next steps"
        next_steps_text = """
            <li>We'll notify you when the threshold is reached</li>
            <li>For hours contributions, we'll contact you to coordinate</li>
            <li>The offering takes place when the community holds it together</li>
        """
        view_offering = "View Offering"
        closing = "Growing together, learning together, regenerating together."
        signature = "The Erdpuls Müllrose Team"
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #2d3748;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            text-align: center;
            padding: 20px 0;
            border-bottom: 2px solid #48bb78;
        }}
        .logo {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        .title {{
            color: #276749;
            font-size: 24px;
            margin: 0;
        }}
        .content {{
            padding: 30px 0;
        }}
        .contribution-box {{
            background: #f0fff4;
            border: 1px solid #9ae6b4;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}
        .contribution-box h3 {{
            margin: 0 0 15px 0;
            color: #276749;
        }}
        .contribution-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #c6f6d5;
        }}
        .contribution-total {{
            font-weight: bold;
            font-size: 1.1em;
            border-top: 2px solid #48bb78;
            margin-top: 10px;
            padding-top: 10px;
        }}
        .privacy-note {{
            background: #ebf8ff;
            border-left: 4px solid #4299e1;
            padding: 12px 16px;
            margin: 20px 0;
            font-size: 0.9em;
        }}
        .next-steps {{
            margin: 20px 0;
        }}
        .next-steps ul {{
            padding-left: 20px;
        }}
        .next-steps li {{
            margin: 8px 0;
        }}
        .cta-button {{
            display: inline-block;
            background: #48bb78;
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 6px;
            margin: 20px 0;
        }}
        .footer {{
            text-align: center;
            padding: 20px 0;
            border-top: 1px solid #e2e8f0;
            color: #718096;
            font-size: 0.9em;
        }}
        .closing {{
            font-style: italic;
            color: #276749;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">&#127793;</div>
        <h1 class="title">Erdpuls Müllrose</h1>
    </div>
    
    <div class="content">
        <p>{greeting}</p>
        <p>{thank_you}</p>
        
        <div class="contribution-box">
            <h3>{your_contribution}</h3>
            <p><strong>{offering_title}</strong></p>
            <div class="contribution-item">
                <span>{contribution_summary}</span>
            </div>
            <div class="contribution-item contribution-total">
                <span>{total_label}</span>
                <span>EUR {total:.2f}</span>
            </div>
        </div>
        
        <div class="privacy-note">
            &#128274; {privacy_note}
        </div>
        
        <div class="next-steps">
            <h3>{next_steps}</h3>
            <ul>
                {next_steps_text}
            </ul>
        </div>
        
        <center>
            <a href="{base_url}/offering/{offering_id}" class="cta-button">{view_offering} &rarr;</a>
        </center>
    </div>
    
    <div class="footer">
        <p class="closing">{closing}</p>
        <p>{signature}<br>
        <a href="{base_url}">erdpuls.ubec.network</a></p>
    </div>
</body>
</html>
"""
    
    # Plain text version
    text_content = f"""
{greeting}

{thank_you}

{your_contribution}: {offering_title}
{contribution_summary}
{total_label}: EUR {total:.2f}

{privacy_note}

{next_steps}:
- We'll notify you when the threshold is reached
- For hours contributions, we'll contact you to coordinate
- The offering takes place when the community holds it together

View offering: {base_url}/offering/{offering_id}

{closing}

{signature}
erdpuls.ubec.network
"""
    
    return send_email(to_email, subject, html_content, text_content)


def send_password_reset_email(
    to_email: str,
    reset_url: str,
    lang: str = 'en'
) -> bool:
    """
    Send a password reset email - minimal plain text to avoid spam filters.
    """
    settings = get_settings()
    
    # Localized content - minimal text
    if lang == 'de':
        subject = f"Erdpuls Müllrose"
        body = f"""Hallo,

Hier ist Ihr Link:

{reset_url}

Der Link ist 1 Stunde gültig.

Erdpuls Müllrose
erdpuls.ubec.network"""
    elif lang == 'pl':
        subject = f"Erdpuls Müllrose"
        body = f"""Cześć,

Oto Twój link:

{reset_url}

Link jest ważny przez 1 godzinę.

Erdpuls Müllrose
erdpuls.ubec.network"""
    else:
        subject = f"Erdpuls Müllrose"
        body = f"""Hello,

Here is your link:

{reset_url}

This link is valid for 1 hour.

Erdpuls Müllrose
erdpuls.ubec.network"""
    
    # Send plain text only - no HTML
    return send_email(to_email, subject, None, body)
