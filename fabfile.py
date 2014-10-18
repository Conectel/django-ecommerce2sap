import os
from fabric.api import env, sudo, cd, local, run, settings, prefix, task
from fabric.operations import get, put, open_shell
from fabric.colors import green, red
from pprint import pprint

REMOTE_BASE_PATH = '/var/www/conectel/'

env.hosts = ['50.116.45.222']
env.user = 'c_aguilar'


def copy_files():
    if os.path.exists('/tmp/conectel.zip'):
        local('rm -r /tmp/conectel.zip')

    local('git archive --format=zip --prefix=conectel/ HEAD > /tmp/conectel.zip')

    put('/tmp/conectel.zip', '/tmp/')

    with cd(REMOTE_BASE_PATH):
        # run('cp www/dwd/settings.py www/dwd/settings_prod.py')
        run('unzip -o /tmp/conectel.zip')
        run('cp -r conectel/* www/')
        # run('cp www/dwd/settings_prod.py www/dwd/settings.py')
        run('rm -r conectel')


def install_deps():
    with cd(REMOTE_BASE_PATH):
        with prefix('source ' + REMOTE_BASE_PATH + 'venv/bin/activate'):
            run('pip install -r www/requirements/requirements.txt')


def collectstatic():
    with cd(REMOTE_BASE_PATH + 'www/'):
        with prefix('source ' + REMOTE_BASE_PATH + 'venv/bin/activate'):
            run('python manage.py collectstatic --noinput')


def run_migrations():
    with cd(REMOTE_BASE_PATH + 'www/'):
        with prefix('source ' + REMOTE_BASE_PATH + 'venv/bin/activate'):
            run('python manage.py migrate')


def restart_supervisord():
    sudo('supervisorctl restart conectel')

def restart_celerybeat():
    sudo('supervisorctl restart celerybeat')

def restart_celery():
    sudo('supervisorctl restart celeryd')

def deploy():
    copy_files()
    install_deps()
    # collectstatic()
    # run_migrations()
    restart_supervisord()
    print(green('Deployed successfully', bold=True))
