"""Read-only source/target release gate; never applies migrations or repairs."""
import argparse
import json
import logging
import os
from pathlib import Path
import sys

from dotenv import dotenv_values
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.tests.rehearse_slice2_release import preflight, data_checks
from backend.tests.postgres_validation_snapshot import snapshot
from backend.migrations.slice2_compat.schema_contract import assert_schema


def run(args):
    logging.disable(logging.CRITICAL)
    settings = dotenv_values(args.env_file)
    engine = create_engine(settings[args.database_variable])
    try:
        state = snapshot(engine, os.urandom(32))
        if args.mode == 'source':
            result = preflight(engine, state)
        else:
            with engine.connect() as connection:
                assert_schema(connection, 'target_schema')
            checks = data_checks(engine, state)
            result = {'data_checks': checks, 'passed': state['revision'] == ['c731retentioncore'] and not any(checks.values())}
        result['revision'] = state['revision']
        result['table_counts'] = {t: state['tables'][t]['count'] for t in ('users', 'supporters', 'support_plans', 'support_records', 'job_retention_contracts', 'audit_action_logs')}
        return result
    finally:
        engine.dispose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', required=True)
    parser.add_argument('--database-variable', default='DATABASE_URL')
    parser.add_argument('--mode', choices=('source', 'target'), required=True)
    try:
        result = run(parser.parse_args())
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0 if result['passed'] else 2)
    except Exception as exc:
        print('RELEASE_CHECK_FAILED:' + type(exc).__name__)
        sys.exit(1)
