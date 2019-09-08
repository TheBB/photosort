import click
import datetime
import io
import itertools
import pydoc
import pyexiv2
from memoized_property import memoized_property
import operator
import os
from os import path
import readline
import shlex

from .gui import run_gui


TZ_OFFSET = 0


def str_or_empty(n):
    return '' if n == 0 else str(n)

def dirnames(directory):
    rest, check = path.split(directory)
    while check != '':
        yield check
        rest, check = path.split(rest)

def is_hidden(root, directory):
    rel = path.relpath(directory, root)
    for name in dirnames(rel):
        if name.startswith('.') and name != '.':
            return True
    return False

def files(root):
    for directory, _, filenames in os.walk(root):
        if is_hidden(root, directory):
            continue
        for filename in filenames:
            yield path.join(directory, filename)

def classify(root, filename):
    basename = path.basename(filename)
    if basename.startswith('.'):
        return None
    if basename.lower() in ('picasa.ini', 'thumbs.db'):
        return None
    base, ext = path.splitext(filename)
    if ext.lower() == '.xmp':
        return 'sidecar'
    if ext.lower() == '.cr2':
        return 'raw'
    if ext.lower() in ('.avi', '.mov', '.mpg', '.mp4'):
        return 'video'
    if ext.lower() in ('.jpg', '.jpeg', '.tif', '.tiff'):
        dirs = list(dirnames(path.relpath(path.dirname(filename), root)))
        if dirs[0].lower() in ('post', 'out'):
            return 'post'
        if dirs[0].lower() in ('pre', 'old'):
            return 'pre'
        return 'pre'
    return None

def rootname(filename, cls, sidecar=True):
    basename = path.basename(filename)
    if cls == 'sidecar':
        if not sidecar:
            return None
        return rootname(path.splitext(filename)[0], sidecar=False)
    return path.splitext(path.basename(filename))[0]

def completer(options):
    matches = []
    def complete(text, state):
        if state == 0:
            matches.clear()
            matches.extend(c for c in options if c.startswith(text))
        return matches[state] if state < len(matches) else None
    return complete


class Media:

    def __init__(self, root):
        self.root = root
        self.description = None
        self.files = {}

    def __setitem__(self, key, val):
        self.files.setdefault(key, []).append(val)

    @property
    def has_photo(self):
        return 'pre' in self.roles()

    def nrole(self, key):
        return len(self.files.get(key, []))

    def roles(self):
        return self.files.keys()

    def summary(self):
        keys = sorted(self.roles)
        return ', '.join('{} {}'.format(len(self.files[k]), k) for k in keys)

    @memoized_property
    def filename(self):
        if 'pre' in self.roles():
            for mediafile in self.files['pre']:
                return mediafile.filename
        return None

    def _query_when(self, allow_stat=False):
        for role in ['raw', 'pre', 'post', 'video']:
            if role not in self.files:
                continue
            for mediafile in self.files[role]:
                when = mediafile.when(allow_stat=allow_stat)
                if when is not None:
                    return when

    @memoized_property
    def when(self):
        when = self._query_when(allow_stat=False)
        if when:
            return when
        return self._query_when(allow_stat=True)


class MediaFile:

    def __init__(self, filename):
        self.filename = filename

    @memoized_property
    def when_exit(self):
        metadata = pyexiv2.ImageMetadata(self.filename)
        try:
            metadata.read()
        except TypeError:
            return None
        if 'Exif.Image.DateTime' in metadata:
            return metadata['Exif.Image.DateTime'].value + datetime.timedelta(hours=TZ_OFFSET)
        return None

    @memoized_property
    def when_stat(self):
        stat = os.stat(self.filename)
        return datetime.datetime.fromtimestamp(stat.st_mtime) + datetime.timedelta(hours=TZ_OFFSET)

    def when(self, allow_stat=False):
        when = self.when_exit
        if when:
            return when
        if allow_stat:
            return self.when_stat


class Files:

    def __init__(self):
        self.files = {}
        self.ignored = []

    def find(self, src):
        sidecars = []
        for fn in files(src):
            cls = classify(src, fn)
            if not cls:
                self.ignored.append(fn)
                continue
            if cls == 'sidecar':
                sidecars.append(fn)
                continue
            root = rootname(fn, cls, sidecar=False)
            self.files.setdefault(root, Media(root))[cls] = MediaFile(fn)

    def finalize(self):
        self.files = sorted(self.files.values(), key=operator.attrgetter('when'))

    def sort(self, by):
        if by == 'time':
            key = operator.attrgetter('when')
        else:
            key = operator.attrgetter('root')
        self.files = sorted(self.files, key=key)

    def next_index(self):
        start = 0
        while self.files[start].description is not None:
            start += 1
        return start

    def candidates(self):
        return self.files[self.next_index():]

    def describe(self, num, desc):
        start = self.next_index()
        for media in self.files[start:start+num]:
            media.description = desc

    def drop(self, num):
        start = self.next_index()
        self.files = self.files[:start] + self.files[start+num:]

    def summary(self, *args):
        roles = {role for media in self.files for role in media.roles()}
        roles = sorted(roles)
        rootlen = max(len(media.root) for media in self.files)
        rolelen = max(len(role) for role in roles)
        datelen = 16
        desclen = 30

        text = io.StringIO()
        def prn(root, date, roles, desc):
            print(f'{root: >{rootlen}}', end='  ', file=text)
            if not isinstance(date, str):
                date = date.strftime('%Y-%m-%d %H:%M')
            print(f'{date: >{datelen}}', end='  ', file=text)
            for role in roles:
                print(f'{role: >{rolelen}}', end='  ', file=text)
            print(desc or '', file=text)

        prn('Name', 'Date', (role.title() for role in roles), 'Description')
        print('-' * (4 + rootlen + datelen + desclen + len(roles) * (rolelen + 2)), file=text)
        for media in self.files:
            prn(media.root, media.when, (str_or_empty(media.nrole(role)) for role in roles), media.description)

        pydoc.pager(text.getvalue())


@click.command()
@click.option('--tzoffset', default=0)
@click.argument('src', type=click.Path(exists=True))
def main(tzoffset, src):
    global TZ_OFFSET
    TZ_OFFSET = tzoffset

    files = Files()
    files.find(src)
    files.finalize()

    readline.set_completer(completer(['summary', 'describe', 'drop']))
    readline.parse_and_bind('tab: complete')
    while True:
        cmd = input('>>> ')
        if not cmd.strip():
            continue
        cmd, *args = shlex.split(cmd)
        if cmd == 'summary':
            files.summary()
        if cmd == 'sort':
            arg, = args
            files.sort(arg)
        if cmd in ('describe', 'drop'):
            num = run_gui(files.candidates())
            if num is None:
                print('No media picked')
                continue
            print(f'Picked {num} media')

            if cmd == 'describe':
                desc = input('Description: ').replace(' ', '_')
                files.describe(num, desc)
            else:
                files.drop(num)


if __name__ == '__main__':
    main()
