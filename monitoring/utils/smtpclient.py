import smtplib
import logging
from email.mime.text import MIMEText


class SMTPClient(object):
    def __init__(self, host, port, use_secure, username, password):
        self.host = host
        self.port = port
        self.use_secure = use_secure
        self.username = username
        self.password = password
        self.smtp_class = smtplib.SMTP_SSL if self.use_secure else smtplib.SMTP
        self.conn = None

    def connect(self):
        logging.debug('Connecting to SMTP host: %s:%s', self.host, self.port)
        self.conn = self.smtp_class(self.host, self.port)
        self.conn.login(self.username, self.password)
        logging.debug('Connected to SMTP host: %s:%s', self.host, self.port)

    def send(self, recipients, subject, message):
        if self.conn is None:
            self.connect()
        msg = MIMEText(message, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = self.username
        msg['To'] = ', '.join(recipients)
        self.conn.sendmail(self.username, recipients, msg.as_string())
