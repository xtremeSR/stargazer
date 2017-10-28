#! python

import logging
from logging.config import dictConfig

from colored import fg, bg, attr


def red(string):
    print '%s%s%s%s' % (fg(1), string, attr(1), attr(0))
    logger.error(string)


def green(string):
    print '%s%s%s%s' % (fg(10), string, attr(1), attr(0))
    logger.info(string)


def yellow(string):
    print '%s%s%s%s' % (fg(11), string, attr(1), attr(0))
    logger.warning(string)


def blue(string):
    print '%s%s%s%s' % (fg(4), string, attr(1), attr(0))
    logger.info(string)


def blue_bg(string):
    print '%s%s%s%s' % (bg(4), string, attr(1), attr(0))
    logger.info(string)


def yellow_bg(string):
    print '%s%s%s%s' % (bg(4), string, attr(1), attr(0))
    logger.info(string)

def string_to_condition(condition):
    condition = condition.split(' ')
    hp_string = condition[0]
    status = condition[1] if len(condition) >= 2 else None
    hp = None
    if hp_string == '0':
        hp = 0.0
    elif '/' in hp_string:
        num, den = hp_string.split('/')
        hp = float(num) / float(den)

    return hp, status

logging_config = dict(
    version=1,
    formatters={
        'f': {'format':
              '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'}
        },
    handlers={
        'h': {'class': 'logging.StreamHandler',
              'formatter': 'f',
              'level': logging.DEBUG}
        },
    loggers={
        'tornado.general': {
            'handlers': ['h'],
            'level': logging.DEBUG
        }
    }
)
dictConfig(logging_config)
logger = logging.getLogger()