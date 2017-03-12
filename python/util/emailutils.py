import os
import smtplib
import smtpd
import mimetypes
import getpass


from email.encoders import encode_base64
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtpd
import asyncore
import thread

COMMASPACE = ', '


class InThreadSMPTServer:
    def __init__(self, localaddr, remoteaddr):
        self.server = smtpd.PureProxy(localaddr, remoteaddr)
        self.thread_id = thread.start_new_thread(asyncore.loop, ())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.server.close()


class EmailSender:
    def __init__(self, serveraddr, login='', with_auth=True):
        self.hostname = serveraddr[0]
        self.port = serveraddr[1]
        self.client = smtplib.SMTP(self.hostname, self.port, timeout=5)
        if with_auth:
            self.client.ehlo()
            self.client.starttls()
            self.client.login(login, getpass.getpass())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.helo()
        self.client.quit()

    @staticmethod
    def __attach_with_filename(outer, filename):
        if type(filename) is not str:
            raise ValueError('filename must be an string')
        path = filename
        if not os.path.isfile(path):
            return None

        # Guess the content type based on the file's extension.  Encoding
        # will be ignored, although we should check for simple things like
        # gzip'd or compressed files.
        ctype, encoding = mimetypes.guess_type(path)
        if ctype is None or encoding is not None:
            # No guess could be made, or the file is encoded (compressed), so
            # use a generic bag-of-bits type.
            ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        if maintype == 'text':
            fp = open(path, 'rb')
            # Note: we should handle calculating the charset
            msg = MIMEText(fp.read(), _subtype=subtype)
            fp.close()
        elif maintype == 'image':
            fp = open(path, 'rb')
            msg = MIMEImage(fp.read(), _subtype=subtype)
            fp.close()
        elif maintype == 'audio':
            fp = open(path, 'rb')
            msg = MIMEAudio(fp.read(), _subtype=subtype)
            fp.close()
        else:
            fp = open(path, 'rb')
            msg = MIMEBase(maintype, subtype)
            msg.set_payload(fp.read())
            fp.close()
            # Encode the payload using Base64
            encode_base64(msg)

        # Set the filename parameter
        msg.add_header('Content-Disposition', 'attachment', filename=path)
        outer.attach(msg)

    @staticmethod
    def __attach_with_buffer(outer, attachment, attachment_name):
        assert attachment_name is not None
        ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        msg = MIMEBase(maintype, subtype)
        msg.set_payload(attachment)
        # Encode the payload using Base64
        encode_base64(msg)

        # Set the filename parameter
        msg.add_header('Content-Disposition', 'attachment', filename=attachment_name)
        outer.attach(msg)

    def compose(self, subject, sender, recipients, attachments_dict):
        outer = MIMEMultipart()
        outer['Subject'] = subject
        outer['To'] = COMMASPACE.join(recipients)
        outer['From'] = sender
        outer.preamble = 'You will not see this in a MIME-aware mail reader.\n'

        for attach_id in attachments_dict:
            attach = attachments_dict[attach_id]
            if type(attach) is str:
                self.__attach_with_filename(outer, attach)
            else:
                # When passing binary streams, we are only accepting one attachment.
                assert len(attachments_dict) is 1
                self.__attach_with_buffer(outer, attach, attach_id)

        return outer

    def send(self, subject, sender, recipients, attachments):
        outer = self.compose(subject, sender, recipients, attachments)
        composed = outer.as_string()
        self.client.sendmail(sender, recipients, composed)

    def __str__(self):
        return self.hostname + ":" + self.port
