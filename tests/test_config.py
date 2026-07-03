from pathlib import Path

from f5authtester.config import load_config
from f5authtester.models import Variant


def test_demo_config_when_no_file(monkeypatch):
    monkeypatch.delenv("F5AUTHTESTER_CONFIG", raising=False)
    monkeypatch.chdir(Path(__file__).parent)  # no config.yaml here
    loaded = load_config()
    assert loaded.source == "demo"
    assert len(loaded.config.targets) == 6
    variants = {t.variant for t in loaded.config.targets}
    assert variants == set(Variant)


def test_load_file_and_env_expansion(tmp_path, monkeypatch):
    monkeypatch.setenv("F5_PASSWORD", "s3cret")
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        """
poll_interval_s: 60
f5:
  enabled: true
  host: bigip.test
  username: svc
  password: ${F5_PASSWORD}
targets:
  - name: KCD App
    variant: kerberos_kcd
    url: https://app.test/
    apm:
      access_profile: ap_app
      sso_config: kcd_app
""",
        encoding="utf-8",
    )
    loaded = load_config(cfg)
    assert loaded.source == str(cfg)
    assert loaded.config.poll_interval_s == 60
    assert loaded.config.f5.password == "s3cret"
    assert loaded.config.targets[0].variant == Variant.KERBEROS_KCD
    assert loaded.config.targets[0].apm.sso_config == "kcd_app"


def test_missing_env_expands_to_empty(tmp_path, monkeypatch):
    monkeypatch.delenv("NOPE", raising=False)
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "targets:\n  - name: X\n    variant: header\n    url: https://x/\n"
        "    probe:\n      bearer_token: ${NOPE}\n",
        encoding="utf-8",
    )
    loaded = load_config(cfg)
    assert loaded.config.targets[0].probe.bearer_token == ""
