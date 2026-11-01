"""Inspect an existing API integration, then optionally deploy its Lambda (bundled with requirements.txt).

Read-only check: python3 scripts/deploy_lambda.py --service order --profile lab7
Deploy:         python3 scripts/deploy_lambda.py --service order --profile lab7 --deploy
Package only:   python3 scripts/deploy_lambda.py --service inventory --package   (writes artifacts/, no AWS calls)
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import unquote
from urllib.request import urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
# service -> (API resource path, HTTP method, backend directory)
SERVICES = {
    'order': ('/order-processing/order', 'POST', 'order-processing'),
    'inventory': ('/inventory-management/inventory', 'GET', 'inventory'),
}


def build_package(source, package, module='lambda_function'):
    """Zip the handler as `module`.py together with the packages in its requirements.txt."""
    with tempfile.TemporaryDirectory(prefix='lambda-deps-') as deps:
        requirements = source / 'requirements.txt'
        if requirements.exists():
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', '--disable-pip-version-check',
                            '-r', str(requirements), '--target', deps], check=True)
        with ZipFile(package, 'w') as archive:
            archive.write(source / 'lambda_function.py', f'{module}.py')
            # The handler looks for the RDS CA bundle next to itself.
            archive.write(ROOT / 'backend/db/rds-ca.pem', str(Path(module).parent / 'rds-ca.pem'))
            parts = module.split('/')[:-1]
            for index in range(len(parts)):
                archive.writestr('/'.join(parts[:index + 1]) + '/__init__.py', '')
            for path in sorted(Path(deps).rglob('*')):
                if path.is_file() and '__pycache__' not in path.parts and not path.parent.name.endswith('.dist-info'):
                    archive.write(path, path.relative_to(deps).as_posix())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--service', choices=SERVICES, default='order')
    parser.add_argument('--profile', default='lab7')
    parser.add_argument('--region', default='us-east-2')
    parser.add_argument('--api-id', default='xnigucru41')
    parser.add_argument('--deploy', action='store_true')
    parser.add_argument('--package', action='store_true', help='only build artifacts/<service>.zip; no AWS calls')
    args = parser.parse_args()
    route, http_method, folder = SERVICES[args.service]
    source = ROOT / 'backend' / folder
    tests = source / 'test_lambda.py'

    if args.package:
        subprocess.run([sys.executable, '-B', str(tests)], check=True)
        (ROOT / 'artifacts').mkdir(exist_ok=True)
        package = ROOT / 'artifacts' / f'{folder}.zip'
        build_package(source, package)
        print(f'Built {package.relative_to(ROOT)} (handler lambda_function.lambda_handler).')
        return

    def aws(*command):
        result = subprocess.run(['aws', *command, '--profile', args.profile, '--region', args.region,
                                 '--output', 'json', '--no-cli-pager'], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr.strip())
        return json.loads(result.stdout) if result.stdout.strip() else None

    resources = aws('apigateway', 'get-resources', '--rest-api-id', args.api_id)
    resource = next((item for item in resources['items'] if item['path'] == route), None)
    if resource is None:
        raise RuntimeError(f'The existing {route} resource was not found; no changes made.')
    integration = aws('apigateway', 'get-integration', '--rest-api-id', args.api_id,
                      '--resource-id', resource['id'], '--http-method', http_method)
    if integration.get('type') != 'AWS_PROXY':
        raise RuntimeError('Expected Lambda proxy integration; no changes made.')
    match = re.search(r'/functions/(arn:[^/]+)/invocations', unquote(integration.get('uri', '')))
    if not match:
        raise RuntimeError('Could not resolve a Lambda ARN from the integration; no changes made.')
    arn = match.group(1)
    if len(arn.split(':')) != 7:
        raise RuntimeError('This integration uses a Lambda alias/version. Resolve its release policy before deployment; no changes made.')
    config = aws('lambda', 'get-function-configuration', '--function-name', arn,
                 '--query', '{FunctionArn:FunctionArn,Handler:Handler,Runtime:Runtime,RevisionId:RevisionId}')
    if not config['Runtime'].startswith('python') or not config['Handler'].endswith('.lambda_handler'):
        raise RuntimeError('The existing Lambda runtime/handler is incompatible; no changes made.')
    print(f"Target: {config['FunctionArn']} ({config['Runtime']}, {config['Handler']})")
    if not args.deploy:
        print('Read-only check passed. Add --deploy to upload the tested Lambda code.')
        return

    subprocess.run([sys.executable, '-B', str(tests)], check=True)
    module = config['Handler'].rsplit('.', 1)[0].replace('.', '/')
    with tempfile.TemporaryDirectory(prefix=f'lab-{args.service}-') as directory:
        package = Path(directory) / f'{folder}.zip'
        build_package(source, package, module)
        # Save the current code before replacing it; do not print its signed download URL.
        previous = aws('lambda', 'get-function', '--function-name', arn, '--query', 'Code.Location')
        backup_dir = ROOT / 'artifacts'
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / f"{args.service}-previous-{config['RevisionId']}.zip"
        with urlopen(previous, timeout=30) as response:
            backup_path.write_bytes(response.read())
        checksum = base64.b64encode(hashlib.sha256(package.read_bytes()).digest()).decode()
        result = aws('lambda', 'update-function-code', '--function-name', arn,
                     '--revision-id', config['RevisionId'], '--zip-file', f'fileb://{package}',
                     '--query', '{CodeSha256:CodeSha256,LastUpdateStatus:LastUpdateStatus}')
        if result['CodeSha256'] != checksum:
            raise RuntimeError('Uploaded code checksum did not match. Inspect Lambda before proceeding.')
        aws('lambda', 'wait', 'function-updated-v2', '--function-name', arn)
        print(f'Deployed and verified code checksum. Previous code saved in {backup_path}')
        print('The existing API Gateway routes are unchanged; Deploy API is not required for this Lambda code update.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
