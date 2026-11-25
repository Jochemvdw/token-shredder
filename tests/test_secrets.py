"""Output goes to AI models: credentials must not leak by default."""
from token_shredder.main import batch_convert, convert_file, find_batch_files

FAKE = {
    "aws": "AKIA" + "ABCDEFGHIJKLMNOP",
    "gh": "ghp_" + "a" * 36,
    "anthropic": "sk-ant-" + "b" * 30,
    "pem": "-----BEGIN RSA PRIVATE KEY-----\nMIIEow" + "c" * 40 + "\n-----END RSA PRIVATE KEY-----",
}


def _conv(path, level=3, **kw):
    return convert_file(str(path), detail_level=level, show_metrics=False, cache_enabled=False,
                        write_output=False, **kw)


def test_secrets_redacted_at_every_level(tmp_path):
    f = tmp_path / "config.py"
    f.write_text("\n".join(f'{k.upper()} = "{v}"' for k, v in FAKE.items() if k != "pem")
                 + f'\nKEY = """{FAKE["pem"]}"""\n')
    for level in range(1, 6):
        r = _conv(f, level)
        for v in FAKE.values():
            assert v not in r.markdown
    assert "[REDACTED: AWS access key]" in _conv(f, 5).markdown
    assert any("redacted" in w for w in _conv(f, 5).warnings)
    assert FAKE["aws"] in _conv(f, 5, redact_secrets=False).markdown


def test_env_values_never_shown(tmp_path):
    f = tmp_path / "prod.env"
    f.write_text("DB_PASSWORD=hunter2\nEMPTY=\nexport API_URL=https://x\n")
    for level in range(1, 6):
        md = _conv(f, level).markdown
        assert "hunter2" not in md and "https://x" not in md
    md = _conv(f).markdown
    assert "DB_PASSWORD" in md and "EMPTY` (empty)" in md and str(tmp_path) not in md


def test_batch_skips_secret_looking_files(tmp_path):
    (tmp_path / "credentials.json").write_text('{"k": "v"}')
    (tmp_path / "client_secret.json").write_text('{"k": "v"}')
    (tmp_path / "app.py").write_text("def f():\n    pass\n")
    skipped = []
    assert [p.name for p in find_batch_files(str(tmp_path), skipped)] == ["app.py"]
    assert sorted(p.name for p in skipped) == ["client_secret.json", "credentials.json"]
    results = batch_convert(str(tmp_path), quiet=True, write_output=False, cache_enabled=False)
    assert len(results) == 1
