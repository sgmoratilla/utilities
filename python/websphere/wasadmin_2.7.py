import time
import os
import sys
from supported_apps import SupportedApps

class AdminApp:
    def __init__(self):
        pass

    @staticmethod
    def list():
        return "List"

    @staticmethod
    def update(app_name, app_type, opts):
        print app_name
        print app_type
        print opts


class AdminConfig:
    def __init__(self):
        pass

    @staticmethod
    def save():
        return "Save"

    @staticmethod
    def reset():
        return "Reset"


class WasApplication:
    def __init__(self, app_name, app_filename, modules_dictionary):
        self.app_name = app_name
        self.app_filename = app_filename
        self.modules_dictionary = modules_dictionary

    def get_change_date(self):
        return os.stat(self.app_filename)[7]

    def wait_change(self):
        last_change_time = self.get_change_date()
        print 'Waiting for change in: ' + self.app_filename + '...'
        while last_change_time == self.get_change_date():
            time.sleep(10)
        print 'Change detected...'

    def get_app_directory(self):
        return os.path.dirname(self.app_filename)

    def print_deploying_info(self):
        print "[Application data: %s from %s]" % (self.app_name, self.app_filename)


class AutoDetectWasApplicationVersion:
    EXTRACT_VERSION_RE = '^[a-zA-Z-]+-([0-9]+.[0-9]+.[0-9]+.[0-9]+.[0-9]+(-SNAPSHOT)?).ear$'

    def __init__(self, app_codename, app_directory, abort_if_several=True):
        self.app_codename = app_codename
        self.app_directory = app_directory
        self.last_version_ear = None
        self.last_version = None
        self.detect_last_version(abort_if_several)

    def detect_last_version(self, abort_if_several=True):
        import glob
        import re

        files = glob.glob(self.app_directory + '/*.ear')
        if len(files) == 0:
            print 'Nothing found to deploy.'
            sys.exit(2)
        elif len(files) > 1:
            if abort_if_several:
                sys.exit(2)
            else:
                print 'Several files detected, deploying higher version.'

        # I think files are already sorted, but documentation says nothing about it.
        files.sort(reverse=True)
        self.last_version_ear = files[0]
        m = re.search(self.EXTRACT_VERSION_RE, os.path.basename(self.last_version_ear))
        if m is None:
            raise ValueError('Not version found in %s' % self.last_version_ear)

        self.last_version = m.group(1)

    def as_was_application(self):
        new_version = {self.app_codename: self.last_version}

        s = SupportedApps(new_version)
        data = s.apps[self.app_codename]

        return WasApplication(data.app_name, data.app_filename, data.modules_dictionary)


class WasConfig:
    def __init__(self, cell, application_server, virtual_host):
        self.cell = cell
        self.application_server = application_server
        self.virtual_host = virtual_host

    @classmethod
    def from_properties(cls, args):
        return cls(cell=args['cell'], application_server=args['application_server'], virtual_host=args['virtual_host'])

    @classmethod
    def default_config_was8(cls):
        was_properties = {'cell': 'was8Node01Cell',
                          'virtual_host': 'default_host',
                          'application_server': 'WebSphere:cell=was8Node01Cell,node=was8Node01,server=server1'}
        return WasConfig.from_properties(was_properties)


class WasAdmin:
    def __init__(self, was_config):
        self.was_config = was_config

    def app_list(self):
        return AdminApp.list()

    def deploy(self, was_application):
        print '  Updating ' + was_application.app_filename
        try:
            map_modules_to_server, map_webmodules_to_vh = self.map_modules(was_application.modules_dictionary)
            opts = ['-operation update -contents {}'.format(was_application.app_filename),
                    '-nopreCompileJSPs -installed.ear.destination $(APP_INSTALL_ROOT)/{}'.format(self.was_config.cell),
                    '-distributeApp -nouseMetaDataFromBinary -nodeployejb -createMBeansForResources -noreloadEnabled -nodeployws -validateinstall warn -noprocessEmbeddedConfig',
                    '-filepermission .*\.dll=755#.*\.so=755#.*\.a=755#.*\.sl=755 -noallowDispatchRemoteInclude -noallowServiceRemoteInclude -asyncRequestDispatchType DISABLED',
                    '-nouseAutoLink -noenableClientModule -clientMode isolated -novalidateSchema',
                    '-MapModulesToServers {}'.format(map_modules_to_server),
                    '-MapWebModToVH {}'.format(map_webmodules_to_vh)]

            AdminApp.update(was_application.app_name, 'app', '[ {} ]'.format(' '.join(opts)))

            print  '   Update Completed, saving config changes'
            AdminConfig.save()
            print '   Config Saved'
        except:
            print '  ERROR on update'
            AdminConfig.reset()
            raise

    def map_modules(self, webmodules_dictionary):
        module_key = list('[')
        module_webmod_to_vh = list('[')
        for module_name in webmodules_dictionary:
            module_path = webmodules_dictionary[module_name]
            m = '[ "{0}" {1},WEB-INF/web.xml {2} ]'.format(module_name, module_path, self.was_config.application_server)
            module_key.append(m)
            m = '[ "{0}" {1},WEB-INF/web.xml {2} ]'.format(module_name, module_path, self.was_config.virtual_host)
            module_webmod_to_vh.append(m)
        module_key.append(']')
        module_webmod_to_vh.append(']')
        map_modules_to_server = ' '.join(module_key)
        map_webmodules_to_vh = ' '.join(module_webmod_to_vh)

        return map_modules_to_server, map_webmodules_to_vh

def parse_arguments():

    import argparse
    parser = argparse.ArgumentParser(description='Updates an enterprise application in WAS')
    parser.add_argument('--auto_update', action='store_true', help='Keep waiting for .ear updates')
    parser.add_argument('--auto_detect_version', action='store_true', help='Trying to auto detect the last version of the application. It checks the deploy directory.')
    parser.add_argument('app_codename', type=str, help='The app codename (i.e: APP10, APP20, ...)')

    return parser.parse_args()


def run():
    args = parse_arguments()

    app = SupportedApps().apps[args.app_codename]
    if args.auto_detect_version:
        auto_detected = AutoDetectWasApplicationVersion(args.app_codename, app.get_app_directory(), abort_if_several=True)
        app = auto_detected.as_was_application()

    was_config = WasConfig.default_config_was8()
    admin = WasAdmin(was_config)
    print '  Current app list:'
    print admin.app_list()

    #app.app_filename = '/tmp/prueba.dat'
    app.print_deploying_info()
    admin.deploy(app)

    if args.auto_update:
        while True:
            admin.deploy(app)
            app.wait_change()
    else:
        admin.deploy(app)

run()
