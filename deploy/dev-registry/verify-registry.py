"""Verify authentication, UI, and eight concurrent small OCI image pushes.

This checks protocol and basic concurrency, not eight full application builds.
Uses only Python's standard library. Credentials are read from a protected file.
"""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import time
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--access-file', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    base = args.url.rstrip('/')
    parsed = urlsplit(base)
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost')):
        parser.error('HTTP is allowed only on loopback')
    access = json.loads(args.access_file.read_text())

    def call(method, path, credentials=None, data=None, headers=None, expected=200):
        target = urljoin(base + '/', path)
        if urlsplit(target).netloc != parsed.netloc:
            raise RuntimeError('Unexpected upload redirect origin')
        h = headers or {}
        if credentials:
            h['Authorization'] = 'Basic ' + base64.b64encode(
                f"{credentials['username']}:{credentials['password']}".encode()).decode()
        req = Request(target, method=method, data=data, headers=h)
        try:
            response = urlopen(req, timeout=120)
        except HTTPError as error:
            if error.code == expected:
                return error.headers, error.read()
            raise RuntimeError(f'{method} {path}: HTTP {error.code}') from None
        with response:
            if response.status != expected:
                raise RuntimeError(f'{method} {path}: expected {expected}, got {response.status}')
            return response.headers, response.read()

    call('GET', '/v2/', expected=401)
    call('GET', '/', expected=401)
    call('GET', '/v2/', {'username': 'team1', 'password': 'incorrect'}, expected=401)
    headers, body = call('GET', '/', access['team1'])
    if '개발 이미지 저장소'.encode() not in body:
        raise RuntimeError('Registry UI did not return expected content')
    tag = 'verify-' + time.strftime('%Y%m%d-%H%M%S', time.gmtime())

    def push(number):
        team = f'team{number}'
        credentials = access[team]
        repo = team + '/registry-smoke'
        # Real 2 MiB random payload in a tar layer; each team gets different bytes.
        buffer = io.BytesIO()
        payload = os.urandom(2 * 1024 * 1024)
        with tarfile.open(fileobj=buffer, mode='w') as archive:
            info = tarfile.TarInfo('verification.bin')
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        layer = buffer.getvalue()
        layer_digest = 'sha256:' + hashlib.sha256(layer).hexdigest()
        config = json.dumps({'architecture': 'amd64', 'os': 'linux',
                             'rootfs': {'type': 'layers', 'diff_ids': [layer_digest]},
                             'config': {'Labels': {'classroom.purpose': 'registry-verification-only'}}}).encode()

        def blob(data):
            digest = 'sha256:' + hashlib.sha256(data).hexdigest()
            h, _ = call('POST', f'/v2/{repo}/blobs/uploads/', credentials, b'', expected=202)
            location = h['Location']
            joiner = '&' if '?' in location else '?'
            call('PUT', location + joiner + 'digest=' + digest, credentials, data,
                 {'Content-Type': 'application/octet-stream'}, expected=201)
            return digest

        blob(layer)
        config_digest = blob(config)
        manifest = json.dumps({'schemaVersion': 2, 'mediaType': 'application/vnd.oci.image.manifest.v1+json',
                               'config': {'mediaType': 'application/vnd.oci.image.config.v1+json',
                                          'digest': config_digest, 'size': len(config)},
                               'layers': [{'mediaType': 'application/vnd.oci.image.layer.v1.tar',
                                           'digest': layer_digest, 'size': len(layer)}]}).encode()
        h, _ = call('PUT', f'/v2/{repo}/manifests/{tag}', credentials, manifest,
                    {'Content-Type': 'application/vnd.oci.image.manifest.v1+json'}, expected=201)
        expected_digest = 'sha256:' + hashlib.sha256(manifest).hexdigest()
        if h['Docker-Content-Digest'] != expected_digest:
            raise RuntimeError('Uploaded manifest digest mismatch')
        h, downloaded = call('GET', f'/v2/{repo}/manifests/{tag}', credentials,
                             headers={'Accept': 'application/vnd.oci.image.manifest.v1+json'})
        if hashlib.sha256(downloaded).hexdigest() != hashlib.sha256(manifest).hexdigest():
            raise RuntimeError('Downloaded manifest mismatch')
        return {'team': team, 'repository': repo, 'tag': tag, 'digest': expected_digest,
                'layer_bytes': len(layer)}

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(push, range(1, 9)))
    # Shared access is intentional: a team1 login CAN read a team2 image.
    call('GET', '/v2/team2/registry-smoke/tags/list', access['team1'])
    report = {'authentication': 'pass', 'ui': 'pass', 'concurrent_pushes': len(results),
              'seconds': round(time.monotonic() - started, 2), 'shared_cross_team_access': True,
              'scope': 'Eight concurrent 2 MiB OCI layer uploads and manifest reads; not application CI load testing',
              'images': results}
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != 'images'}, indent=2))


if __name__ == '__main__':
    main()
