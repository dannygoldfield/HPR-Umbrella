"""Serve the private HPR review with the byte ranges required by media players."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import os


class ReviewHandler(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def send_head(self):
        self.remaining = None
        requested = self.headers.get('Range')
        path = Path(self.translate_path(self.path))
        if not requested or not path.is_file() or self.headers.get('If-Range'):
            return super().send_head()
        match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested.strip())
        # A server may ignore unsupported ranges (including multipart requests).
        if not match or not any(match.groups()):
            return super().send_head()
        try:
            source = path.open('rb')
        except OSError:
            return super().send_head()
        info = os.fstat(source.fileno()); size = info.st_size
        first, last = match.groups()
        if first:
            start = int(first); stop = min(int(last), size-1) if last else size-1
        else:
            start = max(0, size-int(last)); stop = size-1
        if start >= size or stop < start:
            source.close()
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return None
        self.remaining = stop-start+1
        source.seek(start)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(str(path)))
        self.send_header('Content-Length', str(self.remaining))
        self.send_header('Content-Range', f'bytes {start}-{stop}/{size}')
        self.send_header('Last-Modified', self.date_time_string(info.st_mtime))
        self.end_headers()
        return source

    def copyfile(self, source, destination):
        try:
            if self.remaining is None:
                return super().copyfile(source, destination)
            while self.remaining:
                block = source.read(min(64*1024, self.remaining))
                if not block:
                    break
                destination.write(block)
                self.remaining -= len(block)
        except (BrokenPipeError, ConnectionResetError):
            # Switching a preview legitimately cancels the previous download.
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8769)
    args = parser.parse_args(); root = args.review.resolve()
    if not all((root/name).is_file() for name in ('index.html', 'review.json')):
        parser.error('Choose the existing private review directory')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(ReviewHandler, directory=str(root)))
    print(f'HPR review: http://127.0.0.1:{args.port}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
