import argparse
import json


def load_json(path):
    with open(path) as fil:
        return json.load(fil)


def parse_args(required_config_keys):
    '''Parse standard command-line args.
    Parses the command-line arguments mentioned in the SPEC and the
    BEST_PRACTICES documents:
    -c,--config     Config file
    -s,--state      State file
    -d,--discover   Run in discover mode
    -p,--properties Properties file: DEPRECATED, please use --catalog instead
    -a,--auth       Establish user consent to retrieve OAuth2.0 credentials
    --catalog       Catalog file
    Returns the parsed args object from argparse. For each argument that
    point to JSON files (config, state, properties), we will automatically
    load and parse the JSON file.
    '''
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-c', '--config',
        help='Config file',
        required=True)

    parser.add_argument(
        '-s', '--state',
        help='State file')

    parser.add_argument(
        '-p', '--properties',
        help='Property selections: DEPRECATED, Please use --catalog instead')

    parser.add_argument(
        '--catalog',
        help='Catalog file')

    parser.add_argument(
        '-d', '--discover',
        action='store_true',
        help='Do schema discovery')

    parser.add_argument(
        '-a', '--auth',
        action='store_true',
        help='Establish user consent to retrieve OAuth2.0 credentials')

    args = parser.parse_args()
    if args.config:
        setattr(args, 'config_path', args.config)
        args.config = load_json(args.config)
    if args.state:
        setattr(args, 'state_path', args.state)
        args.state = load_json(args.state)
    else:
        args.state = {}
    if args.properties:
        setattr(args, 'properties_path', args.properties)
        args.properties = load_json(args.properties)

    check_config(args.config, required_config_keys)

    return args


def check_config(config, required_keys):
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise Exception("Config is missing required keys: {}".format(missing_keys))
