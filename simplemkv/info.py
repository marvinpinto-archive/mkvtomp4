import sys
import os
import re
import subprocess as sp

try:
    from .version import __version__
except ImportError:
    __version__ = 'unknown'

def indent_level(line):
    """Get the indent level for a line of mkvinfo output.
    Returns -1 if *line* is not the correct format."""
    m = re.search(r'^\|( *)\+', line)
    if not m:
        return -1
    return len(m.group(1))


class TrackLineHandler:
    'Parse a line of (English) mkvinfo output inside "A track".'
    _number   = '|  + Track number: '
    _type     = '|  + Track type: '
    _codec    = '|  + Codec ID: '
    _lang     = '|  + Language: '
    _duration = '|  + Default duration: '
    _fps_re = re.compile(r'\((.*?) frames/fields per second for a video track\)')

    def __init__(self, infodict):
        self._info = infodict

    def _findvalue(self, key, s):
        idx = s.find(key)
        if idx != -1:
            return s[idx + len(key):]
        return None

    def line(self, handlers, l):
        self._track = self._info['tracks'][-1]
        cls = TrackLineHandler
        ind = indent_level(l)
        if ind == -1 or ind < 2:
            handlers.pop(-1)
            return False
        number = self._findvalue(cls._number, l)
        if number:
            endidx = number.find(' ')
            if endidx == -1:
                number = int(number)
            else:
                number = int(number[:endidx])
            self._track['number'] = number - 1
            return True
        typ = self._findvalue(cls._type, l)
        if typ:
            self._track['type'] = typ
            return True
        codec = self._findvalue(cls._codec, l)
        if codec:
            self._track['codec'] = codec
            return True
        lang = self._findvalue(cls._lang, l)
        if lang:
            self._track['language'] = lang
            return True
        if self._track.get('type', '') == 'video':
            duration = self._findvalue(cls._duration, l)
            if duration:
                match = cls._fps_re.search(l)
                if match:
                    self._track['fps'] = float(match.group(1))
                    return True
        return True


class MainLineHandler:
    "Parse a line of (locale='en_US') mkvinfo output."
    def __init__(self, infodict):
        self._info = infodict
        self._track = TrackLineHandler(infodict)

    def line(self, handlers, l):
        if l.startswith('|+ Segment tracks'):
            self._info.setdefault('tracks', [])
            return True
        elif l.startswith('| + A track'):
            self._info['tracks'].append({})
            handlers.append(self._track)
            return True
        return True


def info_locale_opts(locale):
    """Example usage with *infostring*::

        opts = info_locale_opts('en_US')
        opts.setdefault('arguments', [])
        opts['arguments'].extend(['-x', '-r', 'mkvinfo.log'])
        opts.setdefault('env', {})
        opts['env']['MTX_DEBUG'] = 'topic'
        print infostring(mkv, **opts)
    """
    return {'arguments': ['--ui-language', locale]}


def infostring(mkv, env=None, arguments=[], errorfunc=sys.exit, mkvinfo=None):
    """Run mkvinfo on the given *mkv* and returns stdout as a single string.

    On failure, calls *errorfunc* with an error string.

    It's likely you'll want to set *env* or *arguments* to use ``'en_US'``
    locale, since that is what *infodict* requires. See
    *info_locale_opts*.
    """
    if not mkvinfo: mkvinfo = 'mkvinfo'
    cmd = [mkvinfo] + arguments + [mkv]
    opts = {}
    if env is not None:
        env.setdefault('PATH', os.environ.get('PATH', ''))
        env.setdefault('SystemRoot', os.environ.get('SystemRoot', ''))
        opts = {'env': env}
    proc = sp.Popen(
        cmd, stdout=sp.PIPE, stderr=sp.PIPE, close_fds=True, **opts
    )
    out, err = proc.communicate()
    if proc.returncode != 0:
        errorfunc('command failed: ' + err.rstrip('\n'))
    return out


def infodict(lines):
    """Take a list of *lines* of ``locale='en_US'`` mkvinfo output and return a
    dictionary of info."""
    inf = {'lines': lines}
    handlers = [MainLineHandler(inf)]
    for l in lines:
        while not handlers[-1].line(handlers, l):
            if not handlers:
                break
        if not handlers:
            break
    return inf


if __name__ == '__main__':
    from pprint import pprint
    mkv = sys.argv[1]
    s = infostring(mkv, arguments=['--ui-language', 'en_US'])
    d = infodict(inf.rstrip('\n').split('\n'))
    del d['lines']
    pprint(d)
