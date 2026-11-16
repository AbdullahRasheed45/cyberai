import hashlib
import io
import tarfile

from rental.report import verify_archive


def test_verify_archive_closes_extracted_member_streams(tmp_path, monkeypatch):
    archive = tmp_path / "evidence.tar.gz"
    payload = b"evidence"
    with tarfile.open(archive, "w:gz") as bundle:
        member = tarfile.TarInfo("evidence.json")
        member.size = len(payload)
        bundle.addfile(member, io.BytesIO(payload))
    original = tarfile.TarFile.extractfile
    streams = []

    def tracked_extract(bundle, member):
        stream = original(bundle, member)
        streams.append(stream)
        return stream

    monkeypatch.setattr(tarfile.TarFile, "extractfile", tracked_extract)
    assert verify_archive(str(archive), {"evidence.json": hashlib.sha256(payload).hexdigest()}) == (
        True,
        [],
    )
    assert streams and all(stream.closed for stream in streams)
