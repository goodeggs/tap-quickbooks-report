import argparse
import json

import pytest

from tap_quickbooks_report.streams import (ProfitAndLossDetailStream,
                                           ProfitAndLossStream)


@pytest.fixture(scope='function')
def config(shared_datadir):
    with open(shared_datadir / 'test.config.json') as f:
        return json.load(f)


@pytest.fixture(scope='function')
def args(config, shared_datadir):
    args = argparse.Namespace()
    setattr(args, 'config', config)
    setattr(args, 'config_path', shared_datadir / 'test.config.json')
    return args


@pytest.fixture(scope='function', params={ProfitAndLossStream, ProfitAndLossDetailStream})
def client(config, args, shared_datadir, request):
    return request.param(config=config,
                         args=args)
