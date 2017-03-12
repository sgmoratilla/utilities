class SupportedApps:
    DEFAULT_LAST_VERSIONS = {
        'APP_VERSION': '1.0.0.0.0-SNAPSHOT',}

    def __init__(self, last_versions=None):
        if last_versions is None:
            last_versions = self.DEFAULT_LAST_VERSIONS
        else:
            last_versions = dict(self.DEFAULT_LAST_VERSIONS + last_versions)

        app_last_version = self.last_versions['APP_VERSION']

        self.apps = \
            {'APP_VERSION':
                WasApplication('Application 1.0',
                               '/home/wasuser/deployments/application-1.0/application-was-%s.ear' % app_last_version,
                               {'Application Module 1 WAR': 'app-module1-war-was-%s.war' % app_last_version,
                                'Application Module 2 WAR': 'app-module2-war-was-%s.war' % app_last_version})
            }
