import time

import empire_media_gc


def test_media_gc_dry_run(tmp_path, monkeypatch):
    media = tmp_path / "media"
    media.mkdir()
    old = media / "old.jpg"
    old.write_bytes(b"x")
    old_ts = time.time() - 90 * 86400
    import os

    os.utime(old, (old_ts, old_ts))
    monkeypatch.setattr(empire_media_gc, "MEDIA_DIR", media)
    n = empire_media_gc.run_media_gc(ttl_days=45, dry_run=True)
    assert n == 1
    assert old.exists()
