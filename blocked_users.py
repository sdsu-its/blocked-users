#! /usr/bin/python
# Written By Tom Paulus, @tompaulus, www.tompaulus.com
from __future__ import print_function
from __future__ import print_function
from __future__ import unicode_literals

import getopt
import json
import logging
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from os.path import expanduser

import requests

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

SQL_CMD = "UPDATE course_users SET row_status = 0,data_src_pk1 = 2 WHERE crsmain_pk1 = (SELECT pk1 FROM course_main WHERE course_id = '%s') AND users_pk1 = (SELECT PK1 FROM users WHERE user_id = '%s');"

class Config(object):
    config_directory = expanduser("~") + ("/" if not expanduser("~").endswith("/") else '') + 'its'

    history_file_path = config_directory + '/processed_users.json'
    history = list()

    form_config_path = config_directory + "/form_config.json"
    form_config = dict()

    config_json_path = config_directory + '/blocked_user_config.json'
    config_dict = {'smtp': dict(),
                   'email': dict(),
                   'typeform': dict()}

    smtp_user = None
    smtp_password = None
    smtp_server = None
    smtp_port = None

    email_from_name = None
    email_from_address = None
    email_to_address = None

    typeform_api_key = None
    typeform_form_uuid = None

    @classmethod
    def load_config(cls):
        """
        Load the Config JSON from the File in the User's Home Dir

        :return: If config file was loaded correctly
         :rtype: bool
        """
        logging.debug("Config Path is: " + cls.config_json_path)

        try:
            with open(cls.config_json_path) as config_file:
                cls.config_dict = json.loads(config_file.read())
        except IOError:
            logging.warn('Config File not found!')
            return False

        try:
            cls.load_properties_from_dict()
        except KeyError:
            logging.error("Malformed Config File")
            return False

        return True

    @classmethod
    def load_properties_from_dict(cls):
        """
        Set the Class variables based on the values in the config dictionary.

        :exception KeyError: Thrown if a Key is not in the Dict
        """
        cls.smtp_user = cls.config_dict['smtp']['user']
        cls.smtp_password = cls.config_dict['smtp']['password']
        cls.smtp_server = cls.config_dict['smtp']['server']
        cls.smtp_port = cls.config_dict['smtp']['port']

        cls.email_from_name = cls.config_dict['email']['from_name']
        cls.email_from_address = cls.config_dict['email']['from_address']
        cls.email_to_address = cls.config_dict['email']['to_address']

        cls.typeform_api_key = cls.config_dict['typeform']['api_key']
        cls.typeform_form_uuid = cls.config_dict['typeform']['form_uuid']

    @classmethod
    def save_config(cls):
        """
        Save the Config File in the User's Home Dir.
        """
        logging.debug("Config Path is: " + cls.config_json_path)

        if not os.path.exists(cls.config_directory):
            os.makedirs(cls.config_directory)

        with open(cls.config_json_path, 'w') as config_file:
            config_json = json.dumps(cls.config_dict)
            logging.debug("Config JSON: " + config_json)
            config_file.write(config_json)

    @classmethod
    def make_config(cls):
        """
        Make the Config Dictionary by polling the user for the corresponding fields.
        Be sure to call .save_config() after this function
        """

        print("Let's Setup the Typeform API, SMTP Server and Sender Settings. "
              "You will be able to confirm your entries at the end.")
        # Prompt For Input

        typeform_api_key = input(
            "Typeform API Key%s: " % (
                ' [' + cls.typeform_api_key + ']' if cls.typeform_api_key is not None else '')).strip()
        if typeform_api_key != '':
            cls.config_dict['typeform']['api_key'] = typeform_api_key

        typeform_form_uuid = input(
            "Form UUID%s: " % (
                ' [' + cls.typeform_form_uuid + ']' if cls.typeform_form_uuid is not None else '')).strip()
        if typeform_form_uuid != '':
            cls.config_dict['typeform']['form_uuid'] = typeform_form_uuid

        smtp_server_input = input(
            "SMTP Server%s: " % (' [' + cls.smtp_server + ']' if cls.smtp_server is not None else '')).strip()
        if smtp_server_input != '':
            cls.config_dict['smtp']['server'] = smtp_server_input

        smtp_port_input = input(
            "SMTP Port%s: " % (' [' + str(cls.smtp_port) + ']' if cls.smtp_port is not None else '')).strip()
        if smtp_port_input != '':
            cls.config_dict['smtp']['port'] = int(smtp_port_input)

        smtp_username_input = input(
            "SMTP Username%s: " % (' [' + cls.smtp_user + ']' if cls.smtp_user is not None else '')).strip()
        if smtp_username_input != '':
            cls.config_dict['smtp']['user'] = smtp_username_input

        smtp_password_input = input(
            "SMTP Password%s: " % (' [' + cls.smtp_password + ']' if cls.smtp_password is not None else '')).strip()
        if smtp_password_input != '':
            cls.config_dict['smtp']['password'] = smtp_password_input

        email_address_input = input(
            "From Address%s: " % (
                ' [' + cls.email_from_address + ']' if cls.email_from_address is not None else '')).strip()
        if email_address_input != '':
            cls.config_dict['email']['from_address'] = email_address_input

        email_name_input = input(
            "From Name%s: " % (' [' + cls.email_from_name + ']' if cls.email_from_name is not None else '')).strip()
        if email_name_input != '':
            cls.config_dict['email']['from_name'] = email_name_input

        to_address_input = input(
            "To Address(es)%s: " % (
                ' [' + cls.email_to_address + ']' if cls.email_to_address is not None else '')).strip()
        if to_address_input != '':
            cls.config_dict['email']['to_address'] = to_address_input

        # Confirm Input
        print("Typeform API Key: {}\n"
              "Typeform UUID: {}\n"
              "SMTP Server: {}\n"
              "SMTP Port: {}\n"
              "SMTP Username: {}\n"
              "SMTP Password: {}\n"
              "From Address: {}\n"
              "From Name: {}\n"
              "To Address(es): {}".format(
            cls.config_dict['typeform']['api_key'],
            cls.config_dict['typeform']['form_uuid'],
            cls.config_dict['smtp']['server'],
            cls.config_dict['smtp']['port'],
            cls.config_dict['smtp']['user'],
            cls.config_dict['smtp']['password'],
            cls.config_dict['email']['from_address'],
            cls.config_dict['email']['from_name'],
            cls.config_dict['email']['to_address']))

        conf = input("Is this correct? [Y/n]")
        if conf.lower() == "y" or conf.lower() == "":
            cls.load_properties_from_dict()
        else:
            cls.make_config()

    @classmethod
    def load_history(cls):
        """
        Load the History JSON from the File in the User's Home Dir

        :return: If config file was loaded correctly
         :rtype: bool
        """
        logging.debug("History Path is: " + cls.history_file_path)

        try:
            with open(cls.history_file_path) as history_file:
                cls.history = json.loads(history_file.read())
        except IOError:
            logging.warn('History File not found!')
            return False

        return True

    @classmethod
    def save_history(cls):
        """
        Save the History File in the User's Home Dir.
        """
        logging.debug("History Path is: " + cls.history_file_path)

        if not os.path.exists(cls.config_directory):
            os.makedirs(cls.config_directory)

        with open(cls.history_file_path, 'w') as history_file:
            history_json = json.dumps(cls.history)
            logging.debug("History JSON: " + history_json)
            history_file.write(history_json)

    @classmethod
    def load_form(cls):
        """
        Load the Form Config JSON from the File in the User's Home Dir

        :return: If config file was loaded correctly
         :rtype: bool
        """
        logging.debug("Form Config Path is: " + cls.form_config_path)

        try:
            with open(cls.form_config_path) as form_config_file:
                cls.form_config = json.loads(form_config_file.read())
        except IOError:
            logging.fatal('Form Config File not found!')
            exit(1)

        return True


class Typeform(object):
    API_ROOT = "https://api.typeform.com/v1/form/"
    LIMIT = 25

    @classmethod
    def get_responses(cls):
        """
        Retrieve LIMIT newest completed responses from the specified Typeform

        :return: Response List
        :rtype: list
        """
        url = cls.API_ROOT + Config.typeform_form_uuid + "?key=" + Config.typeform_api_key + "&completed=true&order_by[]=date_submit,desc&limit=" + str(
            cls.LIMIT)
        logging.debug("Making Request to Typeform: \n" + url)

        request = requests.get(url)
        form_responses = list()

        if request.status_code != 200:
            logging.warn("Request for Typeform Responses Failed, Code: %d" % request.status_code)
        else:
            logging.debug("Typeform Request Returned Code: %d" % request.status_code)

        try:
            form_responses = request.json()['responses']
            logging.info("Retrieved %d responses from Typeform" % len(form_responses))

        except ValueError as e:
            logging.fatal("Could NOT parse Typeform Response Data - JSON Invalid", e)
            exit(1)

        except KeyError as e:
            logging.error("API Response does not contain any response information", e)

        return form_responses


class Email(object):

    def __init__(self):
        self.smtpserver = smtplib.SMTP(Config.smtp_server, Config.smtp_port)
        self.subject = ''
        self.html_message = ''

    def send(self, to):
        """
        Send the Message to the Recipient

        :param to: Format "Recipient Name <email@address.tdl>"
        :type to: str
        :return: Message Send Status
         :rtype: bool
        """
        try:
            msgRoot = MIMEMultipart('related')
            msgRoot['Subject'] = self.subject
            msgRoot['From'] = "%s <%s>" % (Config.email_from_name, Config.email_from_address)
            msgRoot['To'] = ", ".join(to)
            msgRoot['Date'] = formatdate(localtime=True)

            msgAlternative = MIMEMultipart('alternative')
            msgRoot.attach(msgAlternative)

            msgText = MIMEText(self.html_message, 'html', _charset='utf-8')
            msgAlternative.attach(msgText)

            self.smtpserver.ehlo()
            self.smtpserver.starttls()
            self.smtpserver.ehlo()
            self.smtpserver.login(Config.smtp_user, Config.smtp_password)
            self.smtpserver.sendmail(Config.smtp_user, to, msgRoot.as_string())
            self.smtpserver.quit()
            return True

        except smtplib.SMTPException as e:
            logging.exception("Problem Sending Message\n" + e.message)
            return False


def process_args(argv):
    update = False

    try:
        opts, args = getopt.getopt(argv, "u", ["update"])
    except getopt.GetoptError:
        print('blocked_users.py')
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', "--help"):
            print('blocked_users.py\n'
                  'Append -u or --update to update the configuration file')
            sys.exit()
        elif opt in ("-u", "--update"):
            update = True
            logging.info('User requested to update config info')

    return update


if __name__ == "__main__":
    updated_requested = process_args(sys.argv[1:])

    if not Config.load_config() or updated_requested:
        Config.make_config()
        Config.save_config()

        if updated_requested:
            sys.exit(0)
    logging.debug("Config Loaded")

    if not Config.load_history():
        logging.info("No History File Found, Creating a New one!")

    if not Config.load_form():
        logging.info("No Form Config File Found, Aborting!")

    responses = Typeform.get_responses()

    email_needed = False
    user_sql = ""
    user_info = ""

    for r in responses:
        if not Config.history.__contains__(r[u'token']):
            # Process Entry
            fname = r[u'answers'][Config.form_config['fname']]
            lname = r[u'answers'][Config.form_config['lname']]
            username = r[u'answers'][Config.form_config['username']]
            course = r[u'answers'][Config.form_config['course']]
            try:
                context = r[u'answers'][Config.form_config['context']]
            except KeyError as e:
                logging.warning("No Context was Provided")
                context = None

            user_info += "%s %s (%s) has been blocked from %s.\n" % (fname, lname, username, course)
            if context is not None and len(context) > 0:
                user_info += "Provided Reason: " + context
            user_info += "\n"

            user_sql += SQL_CMD % (course, username) + "\n"

            Config.history.append(r[u'token'])
            email_needed = True
        else:
            # Already Processed
            logging.info("Already Processed Entry - " + r[u'token'])

    message = ""
    with open("./email_template.html") as template_file:
        message = template_file.read()

    message = message \
        .replace("{{ generated_on_date_footer }}", formatdate(localtime=True)) \
        .replace("{{ blocked_user_info }}", user_info.replace("\n", "<br/>")) \
        .replace("{{ blocked_user_sql }}", user_sql.replace("\n", "<br/>"))

    if email_needed:
        email = Email()
        email.html_message = message
        email.subject = "Blocked Users Digest"
        email.send(Config.email_to_address.split(","))
    else:
        logging.info("No email needed as no users were blocked for the current period")

    Config.save_history()
