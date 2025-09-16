import os

from app.core.config import load_s3_config


def test_load_s3_config_prefers_s3_envs(monkeypatch):
    monkeypatch.setenv("S3_ENDPOINT", "http://example:9000")
    monkeypatch.setenv("S3_ACCESS_KEY", "ak")
    monkeypatch.setenv("S3_SECRET_KEY", "sk")
    monkeypatch.setenv("S3_BUCKET", "bucket1")
    monkeypatch.setenv("S3_SECURE", "true")

    cfg = load_s3_config()
    assert cfg.endpoint == "http://example:9000"
    assert cfg.access_key == "ak"
    assert cfg.secret_key == "sk"
    assert cfg.bucket == "bucket1"
    assert cfg.secure is True


def test_load_s3_config_supports_minio_aliases(monkeypatch):
    # Clear S3_* if present in host env
    for key in ["S3_ENDPOINT", "S3_ACCESS_KEY", "S3_SECRET_KEY", "S3_BUCKET", "S3_SECURE"]:
        os.environ.pop(key, None)

    monkeypatch.setenv("MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "aka")
    monkeypatch.setenv("MINIO_SECRET_KEY", "ska")
    monkeypatch.setenv("MINIO_BUCKET", "bucket2")

    cfg = load_s3_config()
    assert cfg.endpoint == "http://minio:9000"
    assert cfg.access_key == "aka"
    assert cfg.secret_key == "ska"
    assert cfg.bucket == "bucket2"
    assert cfg.secure is False
