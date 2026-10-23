"""Focused download/TLS regression checks; no model weights or GPU required."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import ssl
import tempfile
import tomllib
import unittest
from unittest.mock import patch

# Never use a developer's saved Hugging Face credentials for a public TLS test.
os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'
import certifi
import httpx
from huggingface_hub import set_client_factory
from huggingface_hub.errors import GatedRepoError, RepositoryNotFoundError

ROOT = Path(__file__).resolve().parents[1]
# Load the real independent utility without importing the GPU/model package.
spec = importlib.util.spec_from_file_location('muscriptor_download', ROOT / 'muscriptor/utils/download.py')
download = importlib.util.module_from_spec(spec)
spec.loader.exec_module(download)
# emSign ECC Root CA - G3, removed by GHSA-6q48-6c7w-9gw2.
REMOVED_ROOTS = {'86a1ecba089c4a8d3bbe2734c612ba341d813e043cf9e8a862cd5c57a36bbe6b'}


def context():
    return ssl.create_default_context(cafile=certifi.where())


class CertifiSecurityTests(unittest.TestCase):
    def test_installed_version_matches_lock(self):
        lock = tomllib.loads((ROOT / 'uv.lock').read_text())
        package = next(p for p in lock['package'] if p['name'] == 'certifi')
        self.assertEqual(certifi.__version__, package['version'])
        self.assertGreaterEqual(tuple(map(int, certifi.__version__.split('.'))), (2026, 10, 19))

    def test_compromised_roots_not_trusted(self):
        self.assertTrue(REMOVED_ROOTS, 'The advisory fingerprint list must not be empty')
        trusted = {hashlib.sha256(c).hexdigest() for c in context().get_ca_certs(binary_form=True)}
        self.assertTrue(trusted.isdisjoint(REMOVED_ROOTS))

    def test_certificate_and_hostname_verification_required(self):
        ctx = context()
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)

    def test_existing_local_download_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            path.write_text('{}')
            self.assertEqual(download.download_if_necessary(path), path)

    def test_missing_local_download_path(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                download.download_if_necessary(Path(directory) / 'missing')

    def test_gated_repository_error_still_actionable(self):
        response = httpx.Response(401, request=httpx.Request('GET', 'https://huggingface.co/api/models/x'))
        for error in (GatedRepoError, RepositoryNotFoundError):
            with self.subTest(error=error.__name__):
                with patch.object(download, 'hf_hub_download', side_effect=error('401', response=response)):
                    with self.assertRaises(download.ModelDownloadError) as raised:
                        download.download_if_necessary('hf://MuScriptor/muscriptor-medium/model.safetensors')
                    self.assertIn('hf auth login', str(raised.exception))


def verify_public_tls():
    # A clean certifi-only context and no environment proxy/system CA fallback.
    # CI provides direct egress; proxied local execution is not claimed as proof.
    set_client_factory(lambda: httpx.Client(verify=context(), trust_env=False, follow_redirects=True, timeout=30))
    with httpx.Client(verify=context(), trust_env=False, timeout=30) as client:
        client.get('https://pypi.org/pypi/certifi/2026.10.19/json').raise_for_status()
    with tempfile.TemporaryDirectory() as directory:
        from huggingface_hub import hf_hub_download
        def public_download(repo_id, filename):
            return hf_hub_download(repo_id, filename, revision='7755beb2da7cb1d3c663ff4a9ad0d0e99437f78f',
                                   cache_dir=directory, token=False, force_download=True)
        with patch.object(download, 'hf_hub_download', side_effect=public_download):
            path = download.download_if_necessary('hf://MuScriptor/assets/README.md')
        if not path.is_file() or not path.read_text().strip():
            raise RuntimeError('Public Hugging Face download was empty')
    print('PASS: direct certifi-verified HTTPS to PyPI and real hf_hub_download of public MuScriptor assets README')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--network', action='store_true')
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CertifiSecurityTests))
    if not result.wasSuccessful():
        raise SystemExit(1)
    if args.network:
        verify_public_tls()
