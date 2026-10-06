"""The 2.0.0 plugin depends only on Tamlinux.

No file the plugin ships may call an `omarchy-*` command, name an
`omarchy-*` layer, read `/usr/share/omarchy`, or read an `OMARCHY_*`
variable. Comments, documentation, and tests are not scanned. ALLOWED lists
the compatibility reads this plugin keeps on purpose.
"""

import os
import re
import unittest
from pathlib import Path

ROOT = Path(os.environ.get('TAM_BOUNDARY_ROOT') or Path(__file__).resolve().parents[1])

FORBIDDEN = re.compile(r'\bomarchy-[a-z0-9]|/usr/share/omarchy|\bOMARCHY_[A-Z]')
COMMENT = ('//', '#', '/*', '*')
SKIP_DIRS = {'.git', 'docs', 'tests', 'upstream', '__pycache__', 'node_modules'}
SKIP_SUFFIXES = {'.md', '.png', '.svg', '.jpg', '.ics'}
SKIP_NAMES = {'LICENSE'}

# (file, pattern): text matching the pattern on a line of that file is a
# deliberate compatibility read, removed before the line is checked.
ALLOWED = []


def shipped_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if name in SKIP_NAMES or path.suffix in SKIP_SUFFIXES:
                continue
            yield path


def offenders(root, allowed=ALLOWED):
    found = []
    for path in shipped_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            lines = path.read_text(encoding='utf-8').splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, 1):
            if line.lstrip().startswith(COMMENT):
                continue
            for file, pattern in allowed:
                if file == rel:
                    line = re.sub(pattern, '', line)
            if FORBIDDEN.search(line):
                found.append(f'{rel}:{number}: {line.strip()}')
    return found


class NoOmarchyDependency(unittest.TestCase):
    maxDiff = None

    def test_no_omarchy_reference_outside_comments(self):
        found = offenders(ROOT)
        self.assertEqual(found, [], 'Omarchy references:\n' + '\n'.join(found))

    def test_every_allowance_is_still_used(self):
        for file, pattern in ALLOWED:
            text = (ROOT / file).read_text(encoding='utf-8')
            self.assertRegex(text, pattern, f'stale allowance: {file} {pattern}')

    def test_scanner_sees_what_it_should(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'docs').mkdir()
            (base / 'docs' / 'x.qml').write_text('omarchy-skipped\n')
            (base / 'a.qml').write_text(
                '  // omarchy-in-a-comment\n'
                '  exe: "/usr/share/omarchy/bin/x"\n'
                '  path: home + "/.local/state/omarchy/x"\n'
                '  WlrLayershell.namespace: "omarchy-x-panel"\n'
                '  env: Quickshell.env("OMARCHY_PATH")\n')
            (base / 'b.py').write_text('# OMARCHY_X in a comment\nos.environ["OMARCHY_Y"]\n')
            self.assertEqual(offenders(base, []), [
                'a.qml:2: exe: "/usr/share/omarchy/bin/x"',
                'a.qml:4: WlrLayershell.namespace: "omarchy-x-panel"',
                'a.qml:5: env: Quickshell.env("OMARCHY_PATH")',
                'b.py:2: os.environ["OMARCHY_Y"]',
            ])
            self.assertEqual(offenders(base, [('b.py', r'OMARCHY_Y')]), [
                'a.qml:2: exe: "/usr/share/omarchy/bin/x"',
                'a.qml:4: WlrLayershell.namespace: "omarchy-x-panel"',
                'a.qml:5: env: Quickshell.env("OMARCHY_PATH")',
            ])


if __name__ == '__main__':
    unittest.main()
