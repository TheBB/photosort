import click
import pyexiv2
import operator
import os
from os import path


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
        return 'raster'
    return None

def rootname(filename, cls, sidecar=True):
    basename = path.basename(filename)
    if cls == 'sidecar':
        if not sidecar:
            return None
        return rootname(path.splitext(filename)[0], sidecar=False)
    return path.splitext(path.basename(filename))[0]


class Media:

    def __init__(self, root):
        self.root = root
        self.files = {}

    def __setitem__(self, key, val):
        self.files.setdefault(key, []).append(val)

    def nrole(self, key):
        return len(self.files.get(key, []))

    def roles(self):
        return self.files.keys()

    def summary(self):
        keys = sorted(self.roles)
        return ', '.join('{} {}'.format(len(self.files[k]), k) for k in keys)

    def when(self):
        for role in ['raw', 'pre', 'post']:
            if role not in self.files:
                continue
            for mediafile in self.files[role]:
                when = mediafile.when()
                if when is not None:
                    return when
        return None


class MediaFile:

    def __init__(self, filename):
        self.filename = filename
        self._when = None

    def when(self):
        if self._when is not None:
            if self._when == 0:
                return None
            return self._when
        metadata = pyexiv2.ImageMetadata(self.filename)
        metadata.read()
        if 'Exif.Image.DateTime' in metadata:
            self._when = metadata['Exif.Image.DateTime'].value
            return self._when
        self._when = 0
        return None


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
        self.videos = [f for f in self.files.values() if 'video' in f.roles()]
        photos = [f for f in self.files.values() if 'video' not in f.roles()]
        self.photos = sorted(photos, key=operator.methodcaller('when'))

    def summary(self):
        roles = {role for media in self.photos for role in media.roles()}
        roles.update({role for media in self.videos for role in media.roles()})
        roles = sorted(roles)
        rootlen = max(len(media.root) for media in self.photos)
        rolelen = max(len(role) for role in roles)
        datelen = 16

        def prn(root, date, roles):
            print(f'{root: >{rootlen}}', end='  ')
            if not isinstance(date, str):
                date = date.strftime('%Y-%m-%d %H:%M')
            print(f'{date: >{datelen}}', end='  ')
            for role in roles:
                print(f'{role: >{rolelen}}', end='  ')
            print()

        prn('Name', 'Date', (role.title() for role in roles))
        print('-' * (2 + rootlen + datelen + len(roles) * (rolelen + 2)))
        for media in self.photos:
            prn(media.root, media.when(), (str_or_empty(media.nrole(role)) for role in roles))
        for media in self.videos:
            prn(media.root, '', (str_or_empty(media.nrole(role)) for role in roles))


@click.command()
@click.argument('src', type=click.Path(exists=True))
def main(src):
    files = Files()
    files.find(src)
    files.finalize()
    files.summary()

        # if kind is None:
        #     _, ext = path.splitext(fn)
        #     print(fn, ext)


if __name__ == '__main__':
    main()
