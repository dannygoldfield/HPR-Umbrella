from functools import partial
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from serve_review import ReviewHandler


class MediaServerTests(unittest.TestCase):
    def test_media_ranges_head_suffix_and_reused_connection(self):
        payload=bytes(range(256))*20
        with TemporaryDirectory() as tmp:
            (Path(tmp)/'sample.wav').write_bytes(payload)
            server=ThreadingHTTPServer(('127.0.0.1',0),partial(ReviewHandler,directory=tmp))
            worker=Thread(target=server.serve_forever,daemon=True);worker.start()
            client=HTTPConnection('127.0.0.1',server.server_port,timeout=3)
            try:
                for requested,expected,start,stop in [('bytes=0-1023',payload[:1024],0,1023),
                    ('bytes=4096-',payload[4096:],4096,len(payload)-1),
                    ('bytes=-16',payload[-16:],len(payload)-16,len(payload)-1)]:
                    client.request('GET','/sample.wav',headers={'Range':requested})
                    response=client.getresponse()
                    self.assertEqual(response.status,206)
                    self.assertEqual(response.getheader('Content-Range'),f'bytes {start}-{stop}/{len(payload)}')
                    self.assertEqual(response.read(),expected)
                client.request('HEAD','/sample.wav',headers={'Range':'bytes=10-19'})
                response=client.getresponse();self.assertEqual(response.status,206)
                self.assertEqual(response.getheader('Content-Length'),'10');self.assertEqual(response.read(),b'')
                client.request('GET','/sample.wav',headers={'Range':'bytes=9000-'})
                response=client.getresponse();self.assertEqual(response.status,416)
                self.assertEqual(response.getheader('Content-Range'),f'bytes */{len(payload)}');response.read()
                client.request('GET','/sample.wav')
                response=client.getresponse();self.assertEqual(response.status,200)
                self.assertEqual(response.getheader('Accept-Ranges'),'bytes')
                self.assertEqual(response.getheader('Cache-Control'),'no-cache')
                self.assertEqual(response.read(),payload)
            finally:
                client.close();server.shutdown();server.server_close();worker.join()


if __name__=='__main__':unittest.main()
