import configparser
import time
import logging
from captchamonitor.fetchers import firefox_with_tor
from captchamonitor.fetchers import tor_browser
from captchamonitor.fetchers import requests
from captchamonitor.fetchers import firefox
from captchamonitor.utils.sqlite import SQLite
from captchamonitor.utils.queue import Queue
from selenium.webdriver.common.utils import is_connectable

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class CaptchaMonitor:
    def run(config_file):

        queue = Queue(config_file)
        queue_size = queue.check()
        if(queue_size > 0) and (queue_size != None):
            logger.info('Found a new request in the queue, cooking...')

            # Retrive parameters for the job in the queue
            queue_params = {}
            queue_params = queue.get_params()
            job_id = queue_params['job_id']
            url = queue_params['url']
            additional_headers = queue_params['additional_headers']
            method = queue_params['method']
            captcha_sign = queue_params['captcha_sign']

            # Run the test using given parameters
            cm = CaptchaMonitor(method, config_file, job_id)
            cm.create_params()
            cm.fetch(url, captcha_sign, additional_headers)
            cm.detect_captcha()
            cm.store_results()

            logger.info('Done, Bon Appetit!')

    def __init__(self, method, config_file, job_id=None):
        self.params = {}
        self.params['method'] = method
        self.params['config_file'] = config_file
        self.params['job_id'] = job_id

        # Set the default values
        self.params['html_data'] = -1

    def create_params(self):
        config_file = self.params['config_file']
        config = configparser.ConfigParser()
        config.read(config_file)

        # The parameters required to run the tests
        self.params['tbb_path'] = config['GENERAL']['tbb_path']
        self.params['db_mode'] = config['GENERAL']['db_mode']
        self.params['tor_socks_host'] = config['GENERAL']['tor_socks_host']
        self.params['tor_socks_port'] = config['GENERAL']['tor_socks_port']

        if(self.params['db_mode'] == 'SQLite'):
            self.params['db_file'] = config['SQLite']['db_file']

    def get_params(self):
        return self.params

    def fetch(self, url, captcha_sign, additional_headers=None):
        results = {}
        self.params['captcha_sign'] = captcha_sign
        self.params['url'] = url
        self.params['time_stamp'] = int(time.time())
        method = self.params['method']
        tbb_path = self.params['tbb_path']
        tor_socks_host = self.params['tor_socks_host']
        tor_socks_port = self.params['tor_socks_port']

        logger.info('Fetching "%s" via "%s"', url, method)

        if(method == 'firefox_with_tor'):
            self.is_tor_running()
            results = firefox_with_tor.run(url=url,
                                           additional_headers=additional_headers,
                                           tor_socks_host=tor_socks_host,
                                           tor_socks_port=tor_socks_port)

        elif(method == 'tor_browser'):
            self.is_tor_running()
            results = tor_browser.run(url=url,
                                      additional_headers=additional_headers,
                                      tbb_path=tbb_path,
                                      tor_socks_host=tor_socks_host,
                                      tor_socks_port=tor_socks_port)

        elif(method == 'requests'):
            results = requests.run(url, additional_headers)

        elif(method == 'firefox'):
            results = firefox.run(url, additional_headers)

        self.params['all_headers'] = results['all_headers']
        self.params['request_headers'] = results['request_headers']
        self.params['response_headers'] = results['response_headers']
        self.params['html_data'] = results['html_data']

    def detect_captcha(self):
        captcha_sign = self.params.get('captcha_sign')
        html_data = self.params.get('html_data')

        logger.debug('Searching for "%s" in "%s"', self.params['captcha_sign'], self.params['url'])

        if(self.params.get('html_data') != -1):
            is_captcha_found = int(html_data.find(captcha_sign) > 0)
            self.params['is_captcha_found'] = is_captcha_found
            if(is_captcha_found == 1):
                logger.info('I found "%s" in "%s"', self.params['captcha_sign'], self.params['url'])

    def store_results(self):
        db_mode = self.params['db_mode']
        job_id = self.params['job_id']
        html_data = self.params['html_data']
        config_file = self.params['config_file']

        if(html_data == -1):
            logger.info('There was an error during the process, cannot save to db')
            return

        logger.info('Saving results to the "%s" database', db_mode)

        if(db_mode == 'SQLite'):
            db = SQLite(self.params)
            if(job_id is None):
                db.insert_results()
            else:
                db.update_results()

    def is_tor_running(self):
        tor_socks_port = self.params['tor_socks_port']
        if not is_connectable(tor_socks_port):
            logger.critical('Is Tor running at port %s? I can\'t detect it', tor_socks_port)