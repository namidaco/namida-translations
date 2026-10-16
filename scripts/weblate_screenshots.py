#!/usr/bin/env python3
# by claude
"""Attaches the docs screenshots to the Weblate source strings they show.

build:  python scripts/weblate_screenshots.py build
upload: WEBLATE_TOKEN=... python scripts/weblate_screenshots.py upload [--dry-run] [--prune]
"""

import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent
MAP_PATH = SCRIPT_DIR / 'screenshot_map.json'
DEFAULT_ARB = REPO_DIR / 'translations' / 'en.arb'
DEFAULT_DOCS = REPO_DIR.parent / 'namida-assets' / 'screenshots' / 'docs'
DEFAULT_SRC = REPO_DIR.parent.parent / 'lib'

PLATFORMS = ('android', 'windows')
THEME = 'dark'
MAX_IMAGE_SIDE = 2000
STRONG_MIN_WORDS = 2
TEMPLATE_MIN_LETTERS = 4
UBIQUITOUS_SHARE = 0.1
PAIR_MAX_UNIT_KEYS = 30
WRAPPED_LINE_ALIGN_SHARE = 0.02
WRAPPED_LINE_MIN_WIDTH_SHARE = 0.45
WRAPPED_LINE_MIN_GAP = -0.3
WRAPPED_LINE_MAX_GAP = 0.9
METHOD_RANK = {'tile': 0, 'ocr': 1, 'tile+code': 2, 'ocr+code': 3}

_LANG_REF = re.compile(r'\blang\.(\w+)')
_PLACEHOLDER = re.compile(r'\{(\w+)\}')
_PLACEHOLDER_MARKER = re.compile(r'qqph(\d+)qq')
_ICU_HEAD = re.compile(r'\s*(\w+)\s*,\s*(plural|select|selectordinal)\s*,', re.S)
_WORD = re.compile(r'[a-z0-9]+')
_LETTERS = re.compile(r'[a-z]{2,}')
_TOKEN_TEXT = re.compile(r'[A-Za-z]{2}|^[\d.,:]+$')
_ENUMERATOR = re.compile(r'\d+[.)]')
_NUMBER_PATTERN = r'\d+(?:[.,]\d+)*'
_SEGMENT_SEPARATOR = re.compile(r'\s[•·|\-–]\s')
_WHITESPACE = re.compile(r'\s+')
_EDGE_SYMBOLS = re.compile(r'^\W+|\W+$')
_QUOTES = str.maketrans({'‘': "'", '’': "'", '“': '"', '”': '"'})
_MIME = {'.webp': 'image/webp', '.png': 'image/png'}


def build(args):
    strings = _Strings(Path(args.arb))
    docs = Path(args.docs)
    code_units = _code_units(Path(args.src), strings.keys)
    index = _read_json(docs / 'index.json')
    tiles = _read_json(docs / 'tiles.json')
    screens_info = _read_json(docs / 'screens.json')
    parents = {screen['id']: screen['parent'] for screen in screens_info}

    shots = [f'{platform}/{THEME}/{screen}.webp' for platform in PLATFORMS for screen in index[platform][THEME]]
    lines_by_shot = _ocr(docs, shots, args.ocr)

    variants_by_shot, oversized = {}, {}
    for shot in shots:
        width, height = _image_size(docs / shot)
        if max(width, height) > MAX_IMAGE_SIDE:
            oversized[shot] = f'{width}x{height}, over the {MAX_IMAGE_SIDE}px weblate limit'
        texts = _ocr_texts(lines_by_shot[shot], width)
        variants_by_shot[shot] = {variant for text in texts for variant in _variants(text)}
    shots_per_text = Counter(variant.lower() for variants in variants_by_shot.values() for variant in variants)
    max_text_shots = len(shots) * UBIQUITOUS_SHARE
    ubiquitous = {text for text, count in shots_per_text.items() if count > max_text_shots}

    unit_sizes = Counter(unit for units in code_units.values() for unit in units)
    pair_units = {key: {unit for unit in units if unit_sizes[unit] <= PAIR_MAX_UNIT_KEYS} for key, units in code_units.items()}
    found = {}
    for shot in shots:
        platform, _, file = shot.split('/')
        theme_tiles = tiles.get(platform, {}).get(THEME, {})
        screen_tiles = theme_tiles.get(Path(file).stem, {}).get('tiles', ())
        tile_titles = [tile['title'] for tile in screen_tiles]
        found[shot] = _match_screen(strings, code_units, pair_units, tile_titles, variants_by_shot[shot], ubiquitous)

    android_screens = set(index['android'][THEME])
    android_keys = {key for shot, keys in found.items() if shot.startswith('android/') and shot not in oversized for key in keys}
    selected = {}
    for shot, keys in found.items():
        if shot in oversized:
            continue
        is_android_fallback = shot.startswith('windows/') and Path(shot).stem in android_screens
        if is_android_fallback:
            keys = {key: method for key, method in keys.items() if key not in android_keys}
        if keys:
            selected[shot] = keys

    shots_by_key = defaultdict(list)
    for shot, keys in selected.items():
        is_windows = shot.startswith('windows/')
        depth = _depth(parents, Path(shot).stem)
        for key, method in keys.items():
            shots_by_key[key].append((METHOD_RANK[method], is_windows, depth, len(keys), shot))
    kept = defaultdict(dict)
    for key, ranked in shots_by_key.items():
        best = sorted(ranked)[:args.max_per_key]
        for *_, shot in best:
            kept[shot][key] = selected[shot][key]

    screens = {shot: dict(sorted(kept[shot].items())) for shot in sorted(kept)}
    found_keys = {key for keys in found.values() for key in keys}
    considered = [shot for shot in shots if not (shot.startswith('windows/') and Path(shot).stem in android_screens)]
    method_counts = Counter(method for keys in screens.values() for method in keys.values())
    stats = {
        'keys_total': len(strings.keys),
        'keys_covered': len(shots_by_key),
        'keys_only_on_oversized': len(found_keys - shots_by_key.keys()),
        'screens_considered': len(considered),
        'screens_uploaded': len(screens),
        'screens_without_keys': sorted(Path(shot).stem for shot in considered if not found[shot]),
        'windows_fallback_screens': sorted(shot for shot in screens if shot.startswith('windows/') and Path(shot).stem in android_screens),
        'associations': sum(len(keys) for keys in screens.values()),
        'methods': dict(sorted(method_counts.items())),
    }
    out = Path(args.out)
    relative_docs = os.path.relpath(docs.resolve(), out.resolve().parent)
    payload = {'root': Path(relative_docs).as_posix(), 'theme': THEME, 'stats': stats, 'skipped': oversized, 'screens': screens}
    out.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"{stats['keys_covered']}/{stats['keys_total']} keys covered, {len(screens)} screenshots, "
          f"{stats['associations']} associations, {len(stats['screens_without_keys'])} screens without keys, "
          f"{len(oversized)} oversized skipped -> {out}")


def _read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _depth(parents, screen):
    if screen not in parents:
        return len(parents)
    depth = 0
    while (screen := parents[screen]) is not None:
        depth += 1
    return depth


def _match_screen(strings, code_units, pair_units, tile_titles, variants, ubiquitous):
    found = {}

    def record(keys, method, text, is_strong):
        is_strong = is_strong and len(keys) == 1
        priority = (is_strong, -METHOD_RANK[method])
        for key in keys:
            previous = found.get(key)
            if previous is not None:
                previous_method, previous_is_strong, _ = previous
                if priority <= (previous_is_strong, -METHOD_RANK[previous_method]):
                    continue
            found[key] = (method, is_strong, text)

    for title in tile_titles:
        text = _clean(title).lower()
        if keys := strings.exact.get(text):
            record(keys, 'tile', text, True)
    for variant in variants:
        text = variant.lower()
        if keys := strings.exact.get(text):
            is_strong = len(_WORD.findall(text)) >= STRONG_MIN_WORDS
            if is_strong or variant in strings.cased:
                record(keys, 'ocr', text, is_strong)
            continue
        for regex, words, key, anchor in strings.templates:
            if anchor in text and regex.fullmatch(text):
                record((key,), 'ocr', text, words >= STRONG_MIN_WORDS)

    strong_units = set()
    weak_texts_by_unit = defaultdict(set)
    for key, (_, is_strong, text) in found.items():
        if text in ubiquitous:
            continue
        if is_strong:
            strong_units |= code_units.get(key, set())
            continue
        for unit in pair_units.get(key, ()):
            weak_texts_by_unit[unit].add(text)
    result = {}
    for key, (method, is_strong, _) in found.items():
        if is_strong:
            result[key] = method
            continue
        is_near_strong = not strong_units.isdisjoint(code_units.get(key, ()))
        is_paired = any(len(weak_texts_by_unit[unit]) > 1 for unit in pair_units.get(key, ()))
        if is_near_strong or is_paired:
            result[key] = f'{method}+code'
    return result


def _ocr_texts(lines, width):
    lines = sorted(lines, key=lambda line: (line[2], line[1]))
    max_offset = width * WRAPPED_LINE_ALIGN_SHARE
    min_wrapped_width = width * WRAPPED_LINE_MIN_WIDTH_SHARE
    parent, child = {}, {}
    for i, (_, x, y, _, _) in enumerate(lines):
        best = None
        for j in range(i):
            _, px, py, pw, ph = lines[j]
            if j in child or abs(px - x) > max_offset or pw < min_wrapped_width:
                continue
            gap = y - py - ph
            is_next_row = WRAPPED_LINE_MIN_GAP * ph <= gap <= WRAPPED_LINE_MAX_GAP * ph
            if is_next_row and (best is None or py > lines[best][2]):
                best = j
        if best is not None:
            parent[i] = best
            child[best] = i
    texts = set()
    for i, line in enumerate(lines):
        if i in parent:
            continue
        texts.add(line[0])
        chain, k = [line[0]], i
        while k in child:
            k = child[k]
            chain.append(lines[k][0])
        if len(chain) > 1:
            texts.add(' '.join(chain))
    return texts


def _variants(text):
    out = set()
    for segment in (text, *_SEGMENT_SEPARATOR.split(text)):
        tokens = segment.split()
        while tokens and (_is_noise(tokens[0]) or _ENUMERATOR.fullmatch(tokens[0])):
            tokens.pop(0)
        while tokens and _is_noise(tokens[-1]):
            tokens.pop()
        out.add(_clean(segment))
        out.add(_clean(' '.join(tokens)))
    out.discard('')
    return out


def _is_noise(token):
    return _TOKEN_TEXT.search(token) is None


def _clean(text):
    text = text.translate(_QUOTES).replace('…', '...')
    text = _WHITESPACE.sub(' ', text).strip()
    return _EDGE_SYMBOLS.sub('', text)


def _code_units(src, keys):
    units = defaultdict(set)
    for path in src.rglob('*.dart'):
        relative = path.relative_to(src).as_posix()
        if relative.startswith('core/translations/'):
            continue
        declaration = 0
        for line in path.read_text(encoding='utf-8').splitlines():
            first = line[:1]
            if first.isalpha() or first == '_':
                declaration += 1
            for key in _LANG_REF.findall(line):
                if key in keys:
                    units[key].add((relative, declaration))
    return units


def _ocr(docs, shots, engine):
    if engine == 'auto':
        engine = 'windows' if sys.platform == 'win32' else 'tesseract'
    if engine == 'windows':
        return _ocr_windows(docs, shots)
    if not shutil.which('tesseract'):
        sys.exit('tesseract is not on PATH')
    return {shot: _ocr_tesseract(docs / shot) for shot in shots}


def _ocr_windows(docs, shots):
    by_path = {str((docs / shot).resolve()): shot for shot in shots}
    lines = {shot: [] for shot in shots}
    with tempfile.TemporaryDirectory() as temp:
        script, listing, out = Path(temp, 'ocr.ps1'), Path(temp, 'list.txt'), Path(temp, 'out.tsv')
        script.write_text(_WINDOWS_OCR_PS, encoding='utf-8-sig')
        listing.write_text('\n'.join(by_path), encoding='utf-8-sig')
        command = ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(script), str(listing), str(out)]
        process = subprocess.run(command, capture_output=True, text=True)
        if process.returncode != 0 or not out.exists():
            sys.exit(f'windows ocr failed:\n{process.stdout}{process.stderr}')
        for row in out.read_text(encoding='utf-8').splitlines():
            path, text, *box = row.split('\t')
            x, y, w, h = map(int, box)
            lines[by_path[path]].append((text, x, y, w, h))
    return lines


def _ocr_tesseract(path):
    process = subprocess.run(['tesseract', str(path), 'stdout', 'tsv'], capture_output=True, text=True, encoding='utf-8', check=True)
    words, boxes = defaultdict(list), {}
    for row in process.stdout.splitlines()[1:]:
        level, _, block, paragraph, line, _, x, y, w, h, _, *text = row.split('\t')
        line_id = (block, paragraph, line)
        word = ''.join(text).strip()
        if level == '4':
            boxes[line_id] = (int(x), int(y), int(w), int(h))
        elif level == '5' and word:
            words[line_id].append(word)
    return [(' '.join(words[line_id]), *box) for line_id, box in boxes.items() if words[line_id]]


_WINDOWS_OCR_PS = r'''
param([string]$List, [string]$Out)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Storage.StorageFile, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Foundation, ContentType = WindowsRuntime]
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, [Type]$type) { $task = $asTask.MakeGenericMethod($type).Invoke($null, @($op)); $task.Wait() | Out-Null; $task.Result }
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('en-US'))
if ($null -eq $engine) { throw 'the en-US ocr language is not installed' }
$rows = [System.Collections.Generic.List[string]]::new()
foreach ($path in (Get-Content -Encoding UTF8 $List)) {
  $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($path)) ([Windows.Storage.StorageFile])
  $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
  $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
  $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
  $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
  foreach ($line in $result.Lines) {
    $rects = $line.Words | % { $_.BoundingRect }
    $x = ($rects | % { $_.X } | Measure -Minimum).Minimum
    $y = ($rects | % { $_.Y } | Measure -Minimum).Minimum
    $right = ($rects | % { $_.X + $_.Width } | Measure -Maximum).Maximum
    $bottom = ($rects | % { $_.Y + $_.Height } | Measure -Maximum).Maximum
    $text = $line.Text -replace '\t', ' '
    $rows.Add(($path, $text, [int]$x, [int]$y, [int]($right - $x), [int]($bottom - $y)) -join "`t")
  }
  $stream.Dispose()
}
[IO.File]::WriteAllLines($Out, $rows, [Text.UTF8Encoding]::new($false))
'''


class _Strings:
    def __init__(self, arb_path):
        arb = _read_json(arb_path)
        self.keys = {key for key in arb if not key.startswith('@')}
        self.exact = defaultdict(set)
        self.cased = set()
        self.templates = []
        for key in sorted(self.keys):
            metadata = arb.get(f'@{key}', {})
            placeholders = metadata.get('placeholders', {})
            numeric = {name for name, placeholder in placeholders.items() if placeholder.get('type') in ('int', 'num', 'double')}
            for text, plural_vars in _expand(arb[key]):
                if '{' not in text:
                    cleaned = _clean(text)
                    self.exact[cleaned.lower()].add(key)
                    self.cased.add(cleaned)
                    continue
                template = _template(text, numeric | plural_vars)
                if template is not None:
                    regex, words, anchor = template
                    self.templates.append((regex, words, key, anchor))
        self.exact.pop('', None)


def _expand(text):
    start = text.find('{')
    if start < 0:
        return [(text, frozenset())]
    end = _closing_brace(text, start)
    tail = _expand(text[end + 1:])
    head_match = _ICU_HEAD.match(text, start + 1, end)
    if head_match is None:
        heads = [(text[:end + 1], frozenset())]
    else:
        variable, kind = head_match[1], head_match[2]
        numeric = frozenset((variable,)) if kind != 'select' else frozenset()
        prefix = text[:start]
        heads, body_start = [], head_match.end()
        while (case_start := text.find('{', body_start, end)) >= 0:
            case_end = _closing_brace(text, case_start)
            case_body = text[case_start + 1:case_end]
            for case_text, case_vars in _expand(case_body):
                heads.append((prefix + case_text, case_vars | numeric))
            body_start = case_end + 1
    return [(head + rest, head_vars | rest_vars) for head, head_vars in heads for rest, rest_vars in tail]


def _closing_brace(text, start):
    depth = 0
    for i in range(start, len(text)):
        char = text[i]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f'unbalanced braces: {text}')


def _template(text, numeric):
    names = _PLACEHOLDER.findall(text)
    literal = _PLACEHOLDER.sub(' ', text).lower()
    literal_words = _LETTERS.findall(literal)
    if sum(len(word) for word in literal_words) < TEMPLATE_MIN_LETTERS:
        return None
    marked = _PLACEHOLDER.sub(lambda m: f'qqph{names.index(m[1])}qq', text)
    escaped = re.escape(_clean(marked).lower())
    pattern = _PLACEHOLDER_MARKER.sub(lambda m: _NUMBER_PATTERN if names[int(m[1])] in numeric else '.+?', escaped)
    anchor = max(literal_words, key=len)
    return re.compile(pattern), len(literal_words), anchor


def _image_size(path):
    with open(path, 'rb') as f:
        head = f.read(32)
    if head[:8] == b'\x89PNG\r\n\x1a\n':
        return struct.unpack('>II', head[16:24])
    if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
        chunk = head[12:16]
        if chunk == b'VP8 ':
            width, height = struct.unpack('<HH', head[26:30])
            return width & 0x3FFF, height & 0x3FFF
        if chunk == b'VP8L':
            bits = int.from_bytes(head[21:25], 'little')
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        if chunk == b'VP8X':
            return int.from_bytes(head[24:27], 'little') + 1, int.from_bytes(head[27:30], 'little') + 1
    raise ValueError(f'unsupported image: {path}')


def upload(args):
    map_path = Path(args.map).resolve()
    data = _read_json(map_path)
    root = (map_path.parent / data['root']).resolve()
    plan = {}
    for relative, keys in data['screens'].items():
        path = root / relative
        width, height = _image_size(path)
        if max(width, height) > MAX_IMAGE_SIDE:
            print(f'skip {relative}: {width}x{height} is over {MAX_IMAGE_SIDE}px')
            continue
        platform = relative.split('/')[0]
        plan[f'{platform}/{path.stem}'] = (path, sorted(keys))

    token = os.environ.get('WEBLATE_TOKEN')
    if args.dry_run and not token:
        for name, (path, keys) in plan.items():
            print(f'sync {name} <- {path.name}: {len(keys)} strings')
        associations = sum(len(keys) for _, keys in plan.values())
        print(f'dry run (offline, no WEBLATE_TOKEN): {len(plan)} screenshots, {associations} associations')
        return
    if not token:
        sys.exit('WEBLATE_TOKEN is not set')

    api = _Api(args.url, token, args.dry_run)
    component = f'{args.project}/{args.component}'
    units_path = f'translations/{component}/{args.language}/units/?page_size=1000'
    units = {unit['context']: unit['id'] for unit in api.pages(units_path)}
    shots_path = f'components/{component}/screenshots/?page_size=1000'
    existing = {shot['name']: shot for shot in api.pages(shots_path)}
    totals = defaultdict(int)
    for name, (path, keys) in plan.items():
        missing = [key for key in keys if key not in units]
        if missing:
            print(f'{name}: not in weblate, skipped: {", ".join(missing)}')
        wanted = {units[key] for key in keys if key in units}
        image = path.read_bytes()
        filename = name.replace('/', '_') + path.suffix
        image_file = {'image': (filename, image, _MIME[path.suffix])}
        shot = existing.get(name)
        if shot is None:
            fields = {'name': name, 'project_slug': args.project, 'component_slug': args.component, 'language_code': args.language}
            created = api.write('POST', 'screenshots/', fields, image_file, f'create {name}')
            shot_id = _id_from_url(created['url']) if created else '<new>'
            linked = set()
            totals['created'] += 1
        else:
            shot_id = shot['id']
            linked = {_id_from_url(unit_url) for unit_url in shot['units']}
            remote_image = api.read_raw(shot['file_url'])
            if remote_image != image:
                api.write('POST', f'screenshots/{shot_id}/file/', {}, image_file, f'replace image of {name}')
                totals['images replaced'] += 1
        for unit_id in sorted(wanted - linked):
            api.write('POST', f'screenshots/{shot_id}/units/', {'unit_id': unit_id}, None, f'link {name} -> unit {unit_id}')
            totals['links added'] += 1
        if args.prune:
            for unit_id in sorted(linked - wanted):
                api.write('DELETE', f'screenshots/{shot_id}/units/{unit_id}/', None, None, f'unlink {name} -> unit {unit_id}')
                totals['links removed'] += 1
    if args.prune:
        for name, shot in existing.items():
            is_managed = name.split('/')[0] in PLATFORMS
            if is_managed and name not in plan:
                api.write('DELETE', f'screenshots/{shot["id"]}/', None, None, f'delete {name}')
                totals['deleted'] += 1
    summary = ', '.join(f'{count} {action}' for action, count in totals.items()) or 'nothing to do'
    prefix = 'dry run: ' if args.dry_run else ''
    print(prefix + summary)


def _id_from_url(url):
    return int(url.rstrip('/').rsplit('/', 1)[1])


class _Api:
    def __init__(self, base_url, token, dry_run):
        self.base = base_url.rstrip('/') + '/api/'
        self.headers = {'Authorization': f'Token {token}', 'Accept': 'application/json', 'User-Agent': 'namida-weblate-screenshots'}
        self.dry_run = dry_run

    def pages(self, path):
        url = self.base + path
        while url:
            page = json.loads(self._request('GET', url))
            yield from page['results']
            url = page['next']

    def read_raw(self, url):
        return self._request('GET', url)

    def write(self, method, path, fields, files, description):
        if self.dry_run:
            print(f'would {description}')
            return None
        if files:
            body, content_type = _multipart(fields, files)
        elif fields:
            body, content_type = urllib.parse.urlencode(fields).encode(), 'application/x-www-form-urlencoded'
        else:
            body, content_type = None, None
        response = self._request(method, self.base + path, body, content_type)
        print(description)
        return json.loads(response) if response else None

    def _request(self, method, url, body=None, content_type=None):
        headers = dict(self.headers)
        if body is not None:
            headers['Content-Type'] = content_type
        request = urllib.request.Request(url, body, headers, method=method)
        for attempt in range(6):
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    return response.read()
            except urllib.error.HTTPError as error:
                if error.code == 429 and attempt < 5:
                    retry_after = int(error.headers.get('Retry-After') or 60)
                    time.sleep(retry_after + 1)
                    continue
                detail = error.read()[:800].decode(errors='replace')
                sys.exit(f'{method} {url} -> {error.code}: {detail}')


def _multipart(fields, files):
    boundary = uuid.uuid4().hex
    parts = []
    for field, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"\r\n\r\n{value}\r\n'.encode())
    for field, (filename, content, mime) in files.items():
        header = f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n'
        parts.append(header.encode() + content + b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    return b''.join(parts), f'multipart/form-data; boundary={boundary}'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)

    build_parser = commands.add_parser('build', help='match screenshots to en.arb keys and write the map')
    build_parser.add_argument('--docs', default=str(DEFAULT_DOCS), help='screenshots/docs folder of namida-assets')
    build_parser.add_argument('--src', default=str(DEFAULT_SRC), help="namida's lib folder")
    build_parser.add_argument('--arb', default=str(DEFAULT_ARB))
    build_parser.add_argument('--out', default=str(MAP_PATH))
    build_parser.add_argument('--ocr', choices=('auto', 'windows', 'tesseract'), default='auto')
    build_parser.add_argument('--max-per-key', type=int, default=3, help='screenshots kept per string, the most specific first')
    build_parser.set_defaults(run=build)

    upload_parser = commands.add_parser('upload', help='create or update the screenshots on weblate, token from WEBLATE_TOKEN')
    upload_parser.add_argument('--map', default=str(MAP_PATH))
    upload_parser.add_argument('--url', default='https://translate.codeberg.org')
    upload_parser.add_argument('--project', default='namida-translations')
    upload_parser.add_argument('--component', default='namicomponent')
    upload_parser.add_argument('--language', default='en', help='source language code')
    upload_parser.add_argument('--dry-run', action='store_true', help='no writes, offline without a token, read-only diff with one')
    upload_parser.add_argument('--prune', action='store_true', help='also unlink strings no longer mapped and delete unmapped android/ and windows/ screenshots')
    upload_parser.set_defaults(run=upload)

    args = parser.parse_args()
    args.run(args)


if __name__ == '__main__':
    main()
