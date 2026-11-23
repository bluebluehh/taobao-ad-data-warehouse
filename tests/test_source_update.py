import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('verify_source_update', Path(__file__).resolve().parents[1]/'scripts/platform/verify_source_update.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SourceUpdate(unittest.TestCase):
    def test_missing_changed_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            root = base/'source'
            root.mkdir()
            archive = base/'update.zip'
            with zipfile.ZipFile(archive, 'w') as out:
                out.writestr(module.PREFIX+'a.py', 'original')
                out.writestr('SOURCE_FILES_SHA256.json', json.dumps({module.PREFIX+'a.py': hashlib.sha256(b'original').hexdigest()}))
            self.assertFalse(module.compare(root, archive)['source_matches'])
            (root/'a.py').write_text('changed')
            self.assertFalse(module.compare(root, archive)['source_matches'])
            (root/'a.py').write_text('original')
            self.assertTrue(module.compare(root, archive)['source_matches'])
            (base/'external').write_text('original')
            (root/'a.py').unlink()
            (root/'a.py').symlink_to(base/'external')
            self.assertFalse(module.compare(root, archive)['source_matches'])

    def test_traversal_and_unlisted_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            for name, listed in [(module.PREFIX+'../escape', True), (module.PREFIX+'extra.py', False)]:
                archive = base/'update.zip'
                with zipfile.ZipFile(archive, 'w') as out:
                    out.writestr(name, 'x')
                    hashes = {name: hashlib.sha256(b'x').hexdigest()} if listed else {'another': '0'*64}
                    out.writestr('SOURCE_FILES_SHA256.json', json.dumps(hashes))
                with self.assertRaises(ValueError):
                    module.compare(base, archive)
