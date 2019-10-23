import logging
import os

import rollbar
import singer
from rollbar.logger import RollbarHandler

from .streams import (ProfitAndLossDetailStream, ProfitAndLossStream,
                      QuickbooksStream)
from .utils import parse_args

ROLLBAR_ACCESS_TOKEN = os.environ["ROLLBAR_ACCESS_TOKEN"]
ROLLBAR_ENVIRONMENT = os.environ["ROLLBAR_ENVIRONMENT"]

LOGGER = singer.get_logger()

rollbar.init(ROLLBAR_ACCESS_TOKEN, ROLLBAR_ENVIRONMENT)
rollbar_handler = RollbarHandler()
rollbar_handler.setLevel(logging.WARNING)
LOGGER.addHandler(rollbar_handler)

AUTH_REQUIRED_CONFIG_KEYS = [
    "client_id",
    "client_secret",
    "environment",
    "redirect_uri"
]

SYNC_REQUIRED_CONFIG_KEYS = [
    "client_id",
    "client_secret",
    "environment",
    "redirect_uri",
    "realm_id"
]


def user_consent(config):
    LOGGER.info('Starting User Consent process..')
    stream = QuickbooksStream(config=config)
    stream.user_consent()


def sync(config):
    LOGGER.info('Starting sync..')
    stream = ProfitAndLossStream(config=config)
    stream.write_schema_message()
    stream.sync()
    stream = ProfitAndLossDetailStream(config=config)
    stream.write_schema_message()
    stream.sync()


def main():
    args = parse_args(required_config_keys=AUTH_REQUIRED_CONFIG_KEYS)
    if args.auth is True:
        try:
            user_consent(config=args.config)
        except Exception:
            LOGGER.exception('Caught exception during User Consent..')
    else:
        args = parse_args(required_config_keys=SYNC_REQUIRED_CONFIG_KEYS)
        try:
            sync(config=args.config)
        except Exception:
            LOGGER.exception('Caught exception during Sync..')


if __name__ == "__main__":
    main()
