from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from jinja2 import Template
import json
import os
import smtplib

from orm import dbconnect, ShakeMap
from util import sc_dir, SC

class NotificationBuilder(object):
    """
    Uses Jinja to build notifications
    """
    def __init__(self):
        pass
    
    @staticmethod
    def build_new_event_html(events=None, notification=None, group=None, name=None, web=False, config=None):
        temp_manager = TemplateManager()
        if not config:
            if name is None and notification is not None:
                config = temp_manager.get_configs('new_event', 
                                                    name=notification.group.template)
            else:
                config = temp_manager.get_configs('new_event', 
                                                    name=name)
        
        if name is None and notification is not None:
            template = temp_manager.get_template('new_event',
                                                name=notification.group.template)
        else:
            template = temp_manager.get_template('new_event',
                                                name=name)
        

        return template.render(events=events,
                               group=group,
                               notification=notification,
                               sc=SC(),
                               config=config,
                               web=web)
    
    @staticmethod
    def build_insp_html(shakemap, name=None, web=False, config=None):
        temp_manager = TemplateManager()
        if not config:
            config = temp_manager.get_configs('inspection', name=name)
        
        template = temp_manager.get_template('inspection', name=name)

        facility_shaking = shakemap.facility_shaking
        if len(facility_shaking) > 0:
            facility_shaking.sort(key=lambda x: x.weight,
                                        reverse=True)

        fac_details = {'all': 0, 'gray': 0, 'green': 0,
                       'yellow': 0, 'orange': 0, 'red': 0}
        
        for fs in facility_shaking:
            fac_details['all'] += 1
            fac_details[fs.alert_level] += 1
        
        sc = SC()
        max_facilities = sc.dict['Notification']['max_facilities']
        if len(facility_shaking) > max_facilities:
            facility_shaking = facility_shaking[:max_facilities]

        return template.render(shakemap=shakemap,
                               facility_shaking=facility_shaking,
                               fac_details=fac_details,
                               sc=SC(),
                               config=config,
                               web=web)

    @staticmethod
    def build_pdf_html(shakemap, name=None, web=False, config=None):
        temp_manager = TemplateManager()
        if not config:
            config = temp_manager.get_configs('pdf', name=name)

        template = temp_manager.get_template('pdf', name=name)

        facility_shaking = shakemap.facility_shaking
        if len(facility_shaking) > 0:
            facility_shaking.sort(key=lambda x: x.weight,
                                        reverse=True)

        fac_details = {'all': 0, 'gray': 0, 'green': 0,
                       'yellow': 0, 'orange': 0, 'red': 0}

        for fs in facility_shaking:
            fac_details['all'] += 1
            fac_details[fs.alert_level] += 1

        colors = {
            'red': '#FF0000',
            'orange': '#FFA500',
            'yellow': '#FFFF00',
            'green': '#50C878',
            'gray': '#AAAAAA'
        }

        return template.render(shakemap=shakemap,
                               facility_shaking=facility_shaking,
                               fac_details=fac_details,
                               sc=SC(),
                               config=config,
                               web=web,
                               colors=colors)

    @staticmethod
    def build_update_html(update_info=None):
        '''
        Builds an update notification using a jinja2 template
        '''
        template_manager = TemplateManager()
        template = template_manager.get_template('system', name='update')

        return template.render(update_info=update_info)

class Mailer(object):
    """
    Keeps track of information used to send emails
    
    If a proxy is setup, Mailer will try to wrap the smtplib module
    to access the smtp through the proxy
    """
    
    def __init__(self):
        # get info from the config
        sc = SC()
        
        self.me = sc.dict['SMTP']['from'] or sc.dict['SMTP']['username']
        self.username = sc.smtp_username
        self.password = sc.smtp_password
        self.server_name = sc.smtp_server
        self.server_port = int(sc.smtp_port)
        self.security = sc.dict['SMTP']['security']
        self.log = ''
        
    def send(self, msg=None, you=None, debug=False):
        """
        Send an email (msg) to specified addresses (you) using SMTP
        server details associated with the object
        """
        server = smtplib.SMTP(self.server_name, self.server_port) #port 587 or 25

        if self.security.lower() == 'tls':
            server.ehlo()
            server.starttls()
            server.ehlo()

        if self.username and self.password:
            server.login(self.username, self.password)

        server.sendmail(self.me, you, msg.as_string())
        server.quit()

class TemplateManager(object):
    """
    Manages templates and configs for emails
    """

    @staticmethod
    def get_configs(not_type, name=None):
        if name is None:
            temp_name = 'default.json'
        else:
            temp_name = name + '.json'
            conf_file = os.path.join(sc_dir(),
                                    'templates',
                                    not_type,
                                    temp_name)

        try:
            # try to find the template
            conf_str = open(conf_file, 'r')
        except Exception:
            # just get the default template if the supplied one doesn't
            # exist
            conf_file = os.path.join(sc_dir(),
                                    'templates',
                                    not_type,
                                    'default.json')
            conf_str = open(conf_file, 'r')

        config = json.loads(conf_str.read())
        conf_str.close()
        return config

    @staticmethod
    def save_configs(not_type, name, config):
        if isinstance(config, dict):
            conf_file = os.path.join(sc_dir(),
                                    'templates',
                                    not_type,
                                    name + '.json')
            conf_str = open(conf_file, 'w')
            conf_str.write(json.dumps(config, indent=4))
            conf_str.close()
            return config
        else:
            return None

    @staticmethod
    def get_template(not_type, name=None):
        if name is None:
            temp_name = 'default.html'
        else:
            temp_name = name + '.html'
            temp_file = os.path.join(sc_dir(),
                                        'templates',
                                        not_type,
                                        temp_name)

        try:
            temp_str = open(temp_file, 'r')
        except Exception:
            temp_file = os.path.join(sc_dir(),
                                        'templates',
                                        not_type,
                                        'default.html')
            temp_str = open(temp_file, 'r')
        
        template = Template(temp_str.read())
        temp_str.close()
        return template

    @staticmethod
    def get_template_string(not_type, name=None):
        temp_name = 'default.html'
        if name is not None:
            temp_name = name + '.html'

        temp_file = os.path.join(sc_dir(),
                                    'templates',
                                    not_type,
                                    temp_name)
        try:
            temp = open(temp_file, 'r')
            temp_str = temp.read()
            temp.close()
            return temp_str
        except Exception:
            return None

    @staticmethod
    def save_template(not_type, name, template_str):
        temp_file = os.path.join(sc_dir(),
                                'templates',
                                not_type,
                                name + '.html')
        temp_file = open(temp_file, 'w')
        temp_file.write(template_str)
        temp_file.close()
        return temp_file

    @staticmethod
    def get_template_names():
        '''
        Get a list of the existing template names
        '''
        temp_folder = os.path.join(sc_dir(),
                                   'templates',
                                   'new_event')
        file_list = os.listdir(temp_folder)

        # get the names of the templates
        just_names = [f.split('.')[0] for f in file_list if f[-5:] == '.json']
        return just_names
    
    def create_new(self, name):
        event_configs = self.get_configs('new_event', 'default')
        event_temp = self.get_template_string('new_event', 'default')

        insp_configs = self.get_configs('inspection', 'default')
        insp_temp = self.get_template_string('inspection', 'default')

        # save configs
        event_configs_saved = self.save_configs('new_event', name, event_configs)
        insp_configs_saved = self.save_configs('inspection', name, insp_configs)
        
        # save templates
        event_template_saved = self.save_template('new_event', name, event_temp)
        insp_template_saved = self.save_template('inspection', name, insp_temp)

        return bool(None not in [event_configs_saved,
                                    insp_configs_saved,
                                    event_template_saved,
                                    insp_template_saved])


def new_event_notification(notifications=None,
                           scenario=False):
    """
    Build and send HTML email for a new event or scenario
    
    Args:
        event (ShakeMap): which ShakeMap the Notification is attached to
        group (Group): The Group that this Notification is being send to
        notification (Notification): The Notification that will be sent
        scenario (bool): True if the user is running a scenario
        
    Returns:
        None
    """
    events = [n.event for n in notifications]
    group = notifications[0].group
    notification = notifications[0]
    
    # aggregate multiple events
    for n in notifications[1:]:
        n.status = 'aggregated'

    # create HTML for the event email
    not_builder = NotificationBuilder()
    message = not_builder.build_new_event_html(events=events, notification=notification)
    
    notification.status = 'Message built'

    #initiate message
    msg = MIMEMultipart()
    
    # attach html
    message_type = 'html' if '<html>' in message else 'plain'
    encoded_message = MIMEText(message.encode('utf-8'), message_type, 'utf-8')
    msg.attach(encoded_message)

    # get and attach map
    for count,event in enumerate(events):
        map_image = open(os.path.join(event.directory_name,
                                      'image.png'), 'rb')
        msg_gmap = MIMEImage(map_image.read(), _subtype='png')
        map_image.close()
        
        msg_gmap.add_header('Content-ID', '<gmap{0}_{1}>'.format(count, notification.shakecast_id))
        msg_gmap.add_header('Content-Disposition', 'inline')
        msg.attach(msg_gmap)
    
    # find the ShakeCast logo
    temp_manager = TemplateManager()
    configs = temp_manager.get_configs('new_event', 
                                        name=notification.group.template)
    logo_str = os.path.join(sc_dir(),'view','assets',configs['logo'])
    
    # open logo and attach it to the message
    logo_file = open(logo_str, 'rb')
    msg_image = MIMEImage(logo_file.read(), _subtype='png')
    logo_file.close()
    msg_image.add_header('Content-ID', '<sc_logo_{0}>'.format(notification.shakecast_id))
    msg_image.add_header('Content-Disposition', 'inline')
    msg.attach(msg_image)
    
    mailer = Mailer()
    me = mailer.me

    # get notification format
    not_format = group.get_notification_format(notification, scenario)

    # get notification destination based on notification format
    you = [user.__dict__[not_format] for user in group.users
            if user.__dict__.get(not_format, False)]
    
    if len(you) > 0:
        if len(events) == 1:
            subject = event.title.encode('utf-8')
        else:
            mags = []
            for e in events:
                if e.event_id == 'heartbeat':
                    mags += ['None']
                else:
                    mags += [e.magnitude]
                    
            subject = '{0} New Events -- Magnitudes: {1}'.format(len(events),
                                                                        str(mags).replace("'", ''))
        
        if scenario is True:
            subject = 'SCENARIO: ' + subject

        msg['Subject'] = subject
        msg['To'] = ', '.join(you)
        msg['From'] = me
        
        mailer.send(msg=msg, you=you)
        
        notification.status = 'sent'
        
    else:
        notification.status = 'not sent - no users'

@dbconnect
def inspection_notification(notification=None,
                            scenario=False,
                            session=None):
    '''
    Create local products and send inspection notification
    
    Args:
        notification (Notification): The Notification that will be sent

    Returns:
        None
    '''
    shakemap = notification.shakemap
    group = notification.group
    error = ''

    has_alert_level, new_inspection, update = check_notification_for_group(
        group,
        notification,
        session=session,
        scenario=scenario
    )

    if has_alert_level and new_inspection:
        try:
            #initiate message
            msg = MIMEMultipart()

            # build the notification
            not_builder = NotificationBuilder()
            message = not_builder.build_insp_html(shakemap, name=group.template)

            # attach html
            message_type = 'html' if '<html>' in message else 'plain'
            encoded_message = MIMEText(message.encode('utf-8'), message_type, 'utf-8')
            msg.attach(encoded_message)

            # check for pdf
            pdf_location = os.path.join(shakemap.directory_name, 'impact.pdf')
            if (os.path.isfile(pdf_location)):
                with open(pdf_location, 'rb') as pdf_file:
                    attach_pdf = MIMEApplication(pdf_file.read(), _subtype='pdf')
                    attach_pdf.add_header('Content-Disposition', 'attachment', filename='impact.pdf')
                    msg.attach(attach_pdf)

            # get and attach shakemap
            msg_shakemap = MIMEImage(shakemap.get_map(), _subtype='jpeg')
            msg_shakemap.add_header('Content-ID', '<shakemap{0}>'.format(shakemap.shakecast_id))
            msg_shakemap.add_header('Content-Disposition', 'inline')
            msg.attach(msg_shakemap)
            
            # find the ShakeCast logo
            temp_manager = TemplateManager()
            configs = temp_manager.get_configs('inspection',
                                        name=notification.group.template)
            logo_str = os.path.join(sc_dir(),'view','assets',configs['logo'])
            
            # open logo and attach it to the message
            logo_file = open(logo_str, 'rb')
            msg_image = MIMEImage(logo_file.read())
            logo_file.close()
            msg_image.add_header('Content-ID', '<sc_logo{0}>'.format(shakemap.shakecast_id))
            msg_image.add_header('Content-Disposition', 'inline')
            msg.attach(msg_image)
            
            mailer = Mailer()
            me = mailer.me

            # get notification format
            not_format = group.get_notification_format(notification, scenario)

            # get notification destination based on notification format
            you = [user.__dict__[not_format] for user in group.users
                    if user.__dict__.get(not_format, False)]
            
            if len(you) > 0:
                subject = '{0} {1}'.format('Inspection - ', shakemap.event.title)

                if scenario is True:
                    subject = 'SCENARIO: ' + subject
                elif update is True:
                    subject = 'UPDATE: ' + subject
                    

                msg['Subject'] = subject
                msg['To'] = ', '.join(you)
                msg['From'] = me
                
                mailer.send(msg=msg, you=you)
                
                notification.status = 'sent'

            else:
                notification.status = 'not sent - no users'
        except Exception as e:
            error = str(e)
            notification.status = 'send failed'
            
    elif new_inspection:
        notification.status = 'not sent: low inspection priority'
    else:
        notification.status = 'not sent: update without impact changes'

    return {'status': notification.status,
            'error': error}

@dbconnect
def check_notification_for_group(group, notification, session=None, scenario=False):
    shakemap = notification.shakemap

    # Check that the inspection status merits a sent notification
    alert_level = shakemap.get_alert_level()

    # check if inspection list has changed
    new_inspection = True
    update = False
    if shakemap.old_maps():
        update = True
        new_inspection = False

        # get the most recent map version
        previous_map = (session.query(ShakeMap)
            .filter(ShakeMap.shakemap_id == shakemap.shakemap_id)
            .filter(ShakeMap.shakemap_version < shakemap.shakemap_version)
            .order_by(ShakeMap.shakemap_version.desc())
        ).first()

        prev_alert_level = previous_map.get_alert_level()

        # ignore changes if they don't merit inspection (grey and None)
        if (((prev_alert_level is None) and 
                (alert_level is None)) or
                ((prev_alert_level == 'gray') and
                (alert_level == 'gray'))):
            new_inspection = False

        # if overall inspection level changes, send notification
        elif prev_alert_level != alert_level:
            new_inspection = True

        # trigger new inspection if the content of the facility_shaking
        # list changes
        elif len(previous_map.facility_shaking) != len(shakemap.facility_shaking):
            new_inspection = True
        else:
            for idx in range(len(shakemap.facility_shaking)):
                if (shakemap.facility_shaking[idx].facility.facility_id !=
                        previous_map.facility_shaking[idx].facility.facility_id):
                    new_inspection = True
                    break

    return group.has_alert_level(alert_level, scenario), new_inspection, update
