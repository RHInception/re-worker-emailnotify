# Copyright (C) 2014 SEE AUTHORS FILE
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Email Notification worker.
"""

import types

import smtplib

from email.mime.text import MIMEText

from reworker.worker import Worker


class EmailNotifyWorkerError(Exception):
    """
    Base exception class for EmailNotifyWorker errors.
    """
    pass


class EmailNotifyWorker(Worker):
    """
    Worker which knows how to push notification via email..
    """

    def process(self, channel, basic_deliver, properties, body, output):
        """
        Sends notifications via email.

        `Params Required`:
            * target: List of persons/channels who will receive the message.
            * msg: The message to send.
        """
        # Ack the original message
        self.ack(basic_deliver)
        corr_id = str(properties.correlation_id)
        # Notify we are starting
        self.send(
            properties.reply_to, corr_id, {'status': 'started'}, exchange='')

        try:
            required_keys = ('slug', 'message', 'phase', 'target')
            try:
                # Remove target from this check
                for key in required_keys[0:3]:
                    if key not in body.keys():
                        raise KeyError()
                    if not type(body[key]) in types.StringTypes:
                        raise ValueError()
                # Check target on it's own since it's a list of strs
                if 'target' not in body.keys():
                    raise KeyError()
                if type(body['target']) is not list:
                    raise ValueError()
                for key in body['target']:
                    # TODO: better verification that it's an email address
                    if not type(key) in types.StringTypes or '@' not in key:
                        raise ValueError()
            except KeyError:
                raise EmailNotifyWorkerError(
                    'Missing a required param. Requires: %s' % str(
                        required_keys))
            except ValueError:
                raise EmailNotifyWorkerError(
                    'All inputs must be str and valid addresses.')

            output.info('Sending notification to %s via email' % ", ".join(
                body['target']))

            for target in body['target']:
                self._send_msg(target, body['slug'], body['message'])

            output.info('Email notification sent!')
            self.app_logger.info('Finished Email notification with no errors.')

            self.send(
                properties.reply_to,
                corr_id,
                {'status': 'completed'},
                exchange=''
            )

        except EmailNotifyWorkerError, fwe:
            # If a EmailNotifyWorkerError happens send a failure,
            # notify and log  the info for review.
            self.app_logger.error('Failure: %s' % fwe)

            self.send(
                properties.reply_to,
                corr_id,
                {'status': 'failed'},
                exchange=''
            )
            output.error(str(fwe))

    def _send_msg(self, target, slug, msg):
        """
        Sends a message via email.

        `Parameters`:
            * target: The person or channel who will receive the message.
            * slug: the subject to use.
            * msg: The message to send.
        """
        email_msg = MIMEText(msg)
        email_msg['To'] = target
        email_msg['Subject'] = slug
        email_msg['From'] = self._config['smtp_from']

        try:
            smtp = smtplib.SMTP(
                self._config['smtp_host'],
                self._config.get('smtp_port', 25))
            smtp.sendmail(
                email_msg['From'],
                email_msg['To'],
                email_msg.as_string())
            smtp.quit()
        except smtplib.socket.error, se:
            raise EmailNotifyWorkerError('Unable to send email: %s' % se)


def main():  # pragma nocover
    from reworker.worker import runner
    runner(EmailNotifyWorker)


if __name__ == '__main__':  # pragma nocover
    main()
