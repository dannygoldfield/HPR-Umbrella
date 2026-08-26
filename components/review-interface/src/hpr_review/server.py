from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
import json
import mimetypes
from pathlib import Path
import re
from typing import Any
from urllib.parse import unquote, urlparse
import webbrowser

from hpr_registry import (
    list_audio_candidates_for_review,
    list_pair_candidates_for_review,
    list_visual_candidates_for_review,
    save_candidate_review,
    save_pair_review,
)


RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)$")


def _candidate(db_path: Path, visual_id: str) -> dict[str, Any]:
    for candidate in list_visual_candidates_for_review(db_path):
        if candidate["visual_id"] == visual_id:
            return candidate
    raise ValueError(f"Unknown visual candidate: {visual_id}")


def _pair(db_path: Path, pair_id: str) -> dict[str, Any]:
    for candidate in list_pair_candidates_for_review(db_path):
        if candidate["pair_id"] == pair_id:
            return candidate
    raise ValueError(f"Unknown pair candidate: {pair_id}")


def _audio_candidate(db_path: Path, audio_id: str) -> dict[str, Any]:
    for candidate in list_audio_candidates_for_review(db_path):
        if candidate["audio_id"] == audio_id:
            return candidate
    raise ValueError(f"Unknown audio candidate: {audio_id}")


class ReviewHandler(BaseHTTPRequestHandler):
    db_path: Path

    def _json(self, status: HTTPStatus, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _index(self) -> None:
        body = (
            resources.files("hpr_review")
            .joinpath("static/index.html")
            .read_bytes()
        )
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _audio_index(self) -> None:
        body = (
            resources.files("hpr_review")
            .joinpath("static/audio.html")
            .read_bytes()
        )
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, *, allow_range: bool) -> None:
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        size = path.stat().st_size
        start, end = 0, size - 1
        partial = False
        range_header = self.headers.get("Range") if allow_range else None
        if range_header:
            match = RANGE_RE.fullmatch(range_header.strip())
            if not match:
                self.send_error(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                return
            if match.group(1):
                start = int(match.group(1))
            if match.group(2):
                end = min(int(match.group(2)), size - 1)
            if start > end or start >= size:
                self.send_error(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                return
            partial = True
        length = end - start + 1
        self.send_response(
            HTTPStatus.PARTIAL_CONTENT if partial else HTTPStatus.OK
        )
        self.send_header(
            "Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        )
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        if allow_range:
            self.send_header("Accept-Ranges", "bytes")
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with path.open("rb") as source:
            source.seek(start)
            remaining = length
            while remaining:
                chunk = source.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._index()
            return
        if parsed.path in {"/audio", "/audio/"}:
            self._audio_index()
            return
        if parsed.path == "/api/audio-candidates":
            candidates = list_audio_candidates_for_review(self.db_path)
            for candidate in candidates:
                audio_id = candidate["audio_id"]
                candidate["media_url"] = f"/audio-media/{audio_id}"
                candidate["manifest_url"] = f"/audio-manifest/{audio_id}"
                try:
                    manifest = json.loads(
                        Path(candidate["manifest_path"]).read_text(encoding="utf-8")
                    )
                except (OSError, json.JSONDecodeError):
                    manifest = {}
                candidate["batch_id"] = manifest.get("batchId", "Unassigned batch")
                candidate["review_position"] = manifest.get("reviewPosition")
                candidate["target_lufs"] = manifest.get("delivery", {}).get(
                    "targetLufs"
                )
                candidate["delivered_lufs"] = manifest.get("delivery", {}).get(
                    "deliveredIntegratedLufs"
                )
                candidate["comparison_name"] = manifest.get("comparisonName")
                candidate["loop_click_check"] = manifest.get(
                    "loopValidation", {}
                ).get("click_check_passed")
            self._json(HTTPStatus.OK, {"candidates": candidates})
            return
        if parsed.path == "/api/candidates":
            candidates = list_visual_candidates_for_review(self.db_path)
            for candidate in candidates:
                visual_id = candidate["visual_id"]
                candidate["media_url"] = f"/media/{visual_id}"
                candidate["manifest_url"] = f"/manifest/{visual_id}"
            self._json(HTTPStatus.OK, {"candidates": candidates})
            return
        if parsed.path == "/api/pairs":
            candidates = list_pair_candidates_for_review(self.db_path)
            for candidate in candidates:
                pair_id = candidate["pair_id"]
                candidate["media_url"] = f"/pair-media/{pair_id}"
                candidate["manifest_url"] = f"/pair-manifest/{pair_id}"
            self._json(HTTPStatus.OK, {"candidates": candidates})
            return
        for prefix, field, allow_range in (
            ("/audio-media/", "media_path", True),
            ("/audio-manifest/", "manifest_path", False),
        ):
            if parsed.path.startswith(prefix):
                try:
                    item = _audio_candidate(
                        self.db_path, unquote(parsed.path[len(prefix) :])
                    )
                    self._file(Path(item[field]), allow_range=allow_range)
                except ValueError as error:
                    self._json(HTTPStatus.NOT_FOUND, {"error": str(error)})
                return
        for prefix, field, allow_range in (
            ("/media/", "media_path", True),
            ("/manifest/", "manifest_path", False),
        ):
            if parsed.path.startswith(prefix):
                try:
                    item = _candidate(self.db_path, unquote(parsed.path[len(prefix) :]))
                    self._file(Path(item[field]), allow_range=allow_range)
                except ValueError as error:
                    self._json(HTTPStatus.NOT_FOUND, {"error": str(error)})
                return
        for prefix, field, allow_range in (
            ("/pair-media/", "media_path", True),
            ("/pair-manifest/", "manifest_path", False),
        ):
            if parsed.path.startswith(prefix):
                try:
                    item = _pair(self.db_path, unquote(parsed.path[len(prefix) :]))
                    self._file(Path(item[field]), allow_range=allow_range)
                except ValueError as error:
                    self._json(HTTPStatus.NOT_FOUND, {"error": str(error)})
                return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        audio_prefix = "/api/audio-reviews/"
        if parsed.path.startswith(audio_prefix):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 1024 * 1024:
                    raise ValueError("Invalid request size")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("Review must be a JSON object")
                review_id = save_candidate_review(
                    self.db_path,
                    subject_kind="audio",
                    subject_id=unquote(parsed.path[len(audio_prefix) :]),
                    rating=payload.get("rating"),
                    rejected=payload.get("rejected") is True,
                    selected=payload.get("selected") is True,
                    notes=payload.get("notes", ""),
                )
                self._json(HTTPStatus.CREATED, {"review_id": review_id})
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        pair_prefix = "/api/pair-reviews/"
        if parsed.path.startswith(pair_prefix):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 1024 * 1024:
                    raise ValueError("Invalid request size")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("Review must be a JSON object")
                review_id = save_pair_review(
                    self.db_path,
                    pair_id=unquote(parsed.path[len(pair_prefix) :]),
                    pair_rating=payload.get("pair_rating"),
                    audio_rating=payload.get("audio_rating"),
                    rejected=payload.get("rejected") is True,
                    selected=payload.get("selected") is True,
                    retire_audio=payload.get("retire_audio") is True,
                    notes=payload.get("notes", ""),
                )
                self._json(HTTPStatus.CREATED, {"review_id": review_id})
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        prefix = "/api/reviews/"
        if not parsed.path.startswith(prefix):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 1024 * 1024:
                raise ValueError("Invalid request size")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Review must be a JSON object")
            review_id = save_candidate_review(
                self.db_path,
                subject_kind="visual",
                subject_id=unquote(parsed.path[len(prefix) :]),
                rating=payload.get("rating"),
                rejected=payload.get("rejected") is True,
                selected=payload.get("selected") is True,
                notes=payload.get("notes", ""),
            )
            self._json(HTTPStatus.CREATED, {"review_id": review_id})
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})


def handler_for(db_path: Path) -> type[ReviewHandler]:
    class BoundReviewHandler(ReviewHandler):
        pass

    BoundReviewHandler.db_path = db_path
    return BoundReviewHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local HPR review interface")
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if not args.db.is_file():
        parser.error(f"Registry does not exist: {args.db}")
    server = ThreadingHTTPServer((args.host, args.port), handler_for(args.db.resolve()))
    url = f"http://{args.host}:{args.port}/"
    print(f"HPR Review is available at {url}")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
