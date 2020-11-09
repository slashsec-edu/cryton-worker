import click
from cryton_worker.etc import config
from cryton_worker.lib import worker


@click.group()
@click.version_option()
def cli() -> None:
    """
    Cryton Worker CLI.

    \f
    :return: None
    """
    pass


@cli.command('start')
@click.option('--install-requirements', is_flag=True,
              help='Install Python requirements from each requirements.txt in modules_dir.')
@click.option('-Ru', '--rabbit-username', type=click.STRING, default=config.RABBIT_USERNAME, show_default=True,
              help='Rabbit login username.')
@click.option('-Rp', '--rabbit-password', type=click.STRING, default=config.RABBIT_PASSWORD, show_default=True,
              help='Rabbit login password.')
@click.option('-Rh', '--rabbit-host', type=click.STRING, default=config.RABBIT_SRV_ADDR, show_default=True,
              help='Rabbit server host.')
@click.option('-RP', '--rabbit-port', type=click.INT, default=config.RABBIT_SRV_PORT, show_default=True,
              help='Rabbit server port.')
@click.option('-p', '--prefix', type=click.STRING, default=config.RABBIT_WORKER_PREFIX, show_default=True,
              help='What prefix should the Worker use.')
@click.option('-cc', '--core-count', type=click.INT, default=config.CORE_COUNT, show_default=True,
              help='How many processes to use for queues.')
@click.option('-mr', '--max-retries', type=click.INT, default=3, show_default=True,
              help='How many times to try to connect.')
def start_worker(install_requirements: bool, rabbit_username: str, rabbit_password: str,
                 rabbit_host: str, rabbit_port: int, prefix: str, core_count: int, max_retries: int) -> None:
    """
    Start worker and try to connect to Rabbit server

    \f
    :param core_count: How many processes to use for queues
    :param prefix: What prefix should the Worker use
    :param rabbit_port: Rabbit server port
    :param rabbit_host: Rabbit server host
    :param rabbit_password: Rabbit login username
    :param rabbit_username: Rabbit login password
    :param max_retries: How many times to try to connect
    :param install_requirements: Install Python requirements from each requirements.txt in modules_dir
    :return: None
    """
    if install_requirements:
        worker.install_modules_requirements()

    worker.start(rabbit_host, rabbit_port, rabbit_username, rabbit_password, prefix, core_count, max_retries)
