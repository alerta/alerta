
from flask import Flask, current_app

try:
    import smtplib
    import socket
    import ssl

    from smtplib import SMTP  # noqa
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
except ImportError:
    pass


class Mailer:

    def __init__(self, app: Flask=None) -> None:
        self.app = None
        if app is not None:
            self.register(app)

    def register(self, app: Flask) -> None:

        self.smtp_host = app.config['SMTP_HOST']
        self.smtp_port = app.config['SMTP_PORT']
        self.mail_localhost = app.config['MAIL_LOCALHOST']
        self.ssl_key_file = app.config['SSL_KEY_FILE']
        self.ssl_cert_file = app.config['SSL_CERT_FILE']

        self.mail_from = app.config['MAIL_FROM']
        self.smtp_username = app.config.get('SMTP_USERNAME', self.mail_from)
        self.smtp_password = app.config['SMTP_PASSWORD']

        self.smtp_use_ssl = app.config['SMTP_USE_SSL']
        self.smtp_starttls = app.config['SMTP_STARTTLS']

    def send_email(self, email: str, subject: str, body: str) -> None:

        msg = MIMEMultipart('related')
        msg['Subject'] = subject
        msg['From'] = self.mail_from
        msg['To'] = email
        msg.preamble = subject

        msg_text = MIMEText(body, 'plain', 'utf-8')
        msg.attach(msg_text)

        try:
            # Create ssl context
            ctx = ssl.create_default_context()
            if self.ssl_key_file and self.ssl_cert_file:
                # Load client certificates
                ctx.load_cert_chain(certfile=self.ssl_cert_file, keyfile=self.ssl_key_file)

            if self.smtp_use_ssl:
                mx = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, local_hostname=self.mail_localhost,
                                      context=ctx)  # type: SMTP
            else:
                mx = smtplib.SMTP(self.smtp_host, self.smtp_port, local_hostname=self.mail_localhost)

            if current_app.debug:
                mx.set_debuglevel(True)

            if self.smtp_starttls:
                mx.starttls(context=ctx)

            if self.smtp_username and self.smtp_password:
                mx.login(self.smtp_username, self.smtp_password)

            mx.sendmail(self.mail_from, [email], msg.as_string())
            mx.quit()

        except smtplib.SMTPException as e:
            current_app.logger.error('Failed to send email : %s', str(e))
        except (socket.error, socket.herror, socket.gaierror) as e:
            current_app.logger.error('Mail server connection error: %s', str(e))
            return
        except Exception as e:
            current_app.logger.error('Unhandled exception: %s', str(e))
