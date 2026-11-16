import pytest

from rental.report import copy_verified_bundle, sha256_file


def test_delivery_receipt_verifies_destination_bytes(tmp_path):
    source = tmp_path / "run" / "bundle.tar.gz"
    source.parent.mkdir()
    source.write_bytes(b"evidence fixture")
    destination = tmp_path / "durable"
    destination.mkdir()
    receipt = copy_verified_bundle(str(source), str(destination))
    assert receipt["readback_verified"]
    assert receipt["sha256"] == sha256_file(str(destination / source.name))
    with pytest.raises(FileExistsError):
        copy_verified_bundle(str(source), str(destination))


def test_delivery_cannot_masquerade_run_directory_as_durable_copy(tmp_path):
    source = tmp_path / "bundle.tar.gz"
    source.write_bytes(b"fixture")
    with pytest.raises(ValueError):
        copy_verified_bundle(str(source), str(tmp_path))
