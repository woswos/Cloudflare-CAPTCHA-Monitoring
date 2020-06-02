#!/usr/bin/env python3

"""
Fetch a given URL using seleniumwire, Firefox, and Tor
"""

import os
import logging
import json
from urltools import compare
from seleniumwire import webdriver
from selenium.webdriver.firefox.options import Options

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def run(url, additional_headers, tor_socks_host, tor_socks_port):
    results = {}

    # Configure seleniumwire to upstream traffic to Tor running on port 9050
    #   You might want to increase/decrease the timeout if you are trying
    #   to a load page that requires a lot of requests. It is in seconds.
    seleniumwire_options = {
        'proxy': {
            'http': 'socks5h://' + tor_socks_host + ':' + tor_socks_port,
            'https': 'socks5h://' + tor_socks_host + ':' + tor_socks_port,
            'connection_timeout': 10
        }
    }

    # Choose the headless mode
    options = Options()
    options.headless = True

    driver = webdriver.Firefox(options=options,
                               seleniumwire_options=seleniumwire_options)

    if additional_headers:
        driver.header_overrides = json.loads(additional_headers)

    # Try sending a request to the server and get server's response
    try:
        driver.get(url)

    except Exception as err:
        logger.error('webdriver.Firefox.get() says: %s' % err)
        return -1

    # Record the results
    results['html_data'] = driver.page_source
    results['all_headers'] = str(driver.requests)

    for request in driver.requests:
        if(compare(request.path, url)):
                results['request_headers'] = json.dumps(dict(request.headers))
                if(request.response):
                    results['response_headers'] = json.dumps(dict(request.response.headers))
                else:
                    results['response_headers'] = " "

    logger.debug('I\'m done fetching %s', url)

    driver.quit()

    return results