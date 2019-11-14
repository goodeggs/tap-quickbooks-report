import logging
import os
import sys

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
    "realm_id",
    "refresh_token",
    "refresh_token_expires_at"
]


def user_consent(config, args):
    LOGGER.info('Starting User Consent process..')
    stream = QuickbooksStream(config=config, args=args)
    stream.user_consent()


def sync(config, args):
    LOGGER.info('Starting sync..')
    stream = ProfitAndLossStream(config=config, args=args)
    stream.write_schema_message()
    stream.sync()
    stream = ProfitAndLossDetailStream(config=config, args=args)
    stream.write_schema_message()
    stream.sync()


def main():
    args = parse_args(required_config_keys=AUTH_REQUIRED_CONFIG_KEYS)
    if args.auth is True:
        try:
            user_consent(config=args.config, args=args)
        except:
            LOGGER.exception('Caught exception during user consent..')
    else:
        args = parse_args(required_config_keys=SYNC_REQUIRED_CONFIG_KEYS)
        try:
            sync(config=args.config, args=args)
        except:
            LOGGER.exception('Caught exception during sync..')


if __name__ == "__main__":
    main()
