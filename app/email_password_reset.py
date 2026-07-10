"""
Password Reset Email Function - Add this to your existing email.py file

© 2024–2026 Michel Garand | License: GNU AGPL v3.0 | https://www.gnu.org/licenses/agpl-3.0.html
"""

# Add this function to your existing app/email.py file


def send_password_reset_email(
    to_email: str,
    reset_url: str,
    lang: str = 'en'
) -> bool:
    """
    Send a password reset email with secure reset link.
    
    Args:
        to_email: Recipient email address
        reset_url: Full URL with token for password reset
        lang: Language code ('en', 'de', 'pl')
    
    Returns:
        True if sent successfully, False otherwise
    """
    settings = get_settings()
    
    # Localized content
    if lang == 'de':
        subject = "Passwort zurücksetzen – Erdpuls Müllrose"
        greeting = "Hallo,"
        intro = "Wir haben eine Anfrage zum Zurücksetzen Ihres Passworts erhalten."
        action_text = "Klicken Sie auf den folgenden Link, um Ihr Passwort zurückzusetzen:"
        button_text = "Passwort zurücksetzen"
        expiry_note = "Dieser Link ist 1 Stunde gültig."
        ignore_note = "Falls Sie diese Anfrage nicht gestellt haben, können Sie diese E-Mail ignorieren. Ihr Passwort wird nicht geändert."
        signature = "Das Erdpuls Müllrose Team"
    elif lang == 'pl':
        subject = "Zresetuj hasło – Erdpuls Müllrose"
        greeting = "Cześć,"
        intro = "Otrzymaliśmy prośbę o zresetowanie Twojego hasła."
        action_text = "Kliknij poniższy link, aby zresetować hasło:"
        button_text = "Zresetuj hasło"
        expiry_note = "Ten link jest ważny przez 1 godzinę."
        ignore_note = "Jeśli nie prosiłeś o zresetowanie hasła, zignoruj tę wiadomość. Twoje hasło nie zostanie zmienione."
        signature = "Zespół Erdpuls Müllrose"
    else:
        subject = "Reset your password – Erdpuls Müllrose"
        greeting = "Hello,"
        intro = "We received a request to reset your password."
        action_text = "Click the link below to reset your password:"
        button_text = "Reset Password"
        expiry_note = "This link is valid for 1 hour."
        ignore_note = "If you didn't request this, you can safely ignore this email. Your password will not be changed."
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
            font-size: 28px;
            margin-bottom: 10px;
        }}
        .content {{
            padding: 30px 0;
        }}
        .button {{
            display: inline-block;
            background-color: #2f5233;
            color: white !important;
            text-decoration: none;
            padding: 14px 28px;
            border-radius: 6px;
            font-weight: 600;
            margin: 20px 0;
        }}
        .button:hover {{
            background-color: #3d6b42;
        }}
        .note {{
            background-color: #f7fafc;
            padding: 15px;
            border-radius: 6px;
            margin: 20px 0;
            font-size: 14px;
            color: #718096;
        }}
        .footer {{
            text-align: center;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
            color: #718096;
            font-size: 14px;
        }}
        .link-text {{
            word-break: break-all;
            font-size: 12px;
            color: #718096;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🌱</div>
        <div><strong>Erdpuls Müllrose</strong></div>
    </div>
    
    <div class="content">
        <p>{greeting}</p>
        <p>{intro}</p>
        <p>{action_text}</p>
        
        <p style="text-align: center;">
            <a href="{reset_url}" class="button">{button_text}</a>
        </p>
        
        <p class="link-text">
            {reset_url}
        </p>
        
        <div class="note">
            <p style="margin: 0;"><strong>{expiry_note}</strong></p>
            <p style="margin: 10px 0 0 0;">{ignore_note}</p>
        </div>
    </div>
    
    <div class="footer">
        <p>{signature}</p>
    </div>
</body>
</html>
"""
    
    text_content = f"""{greeting}

{intro}

{action_text}

{reset_url}

{expiry_note}

{ignore_note}

{signature}
"""
    
    return send_email(
        to_email=to_email,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )
