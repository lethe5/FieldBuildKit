"""The independent app must coexist without sharing the old app's state."""
from pathlib import Path

from qfield_builder import __version__, credential_store
from qfield_builder.ui import app, wizard

# Keep the real resolver before the suite's autouse credential-isolation fixture replaces it.
_real_app_data_dir = credential_store.app_data_dir


def test_distribution_command_bundle_and_version_are_independent():
    root = Path(__file__).resolve().parents[2]
    project = (root / "pyproject.toml").read_text()
    assert 'name = "fieldbuild-standalone"' in project
    assert f'version = "{__version__}"' in project
    assert __version__ == "0.1.0"
    assert 'fieldbuild-standalone = "qfield_builder.ui.app:main"' in project
    assert wizard.APP_DISPLAY_NAME == "FieldBuild Standalone"
    spec = (root / "packaging/qfield_builder.spec").read_text()
    assert 'bundle_identifier="kr.re.nie.fieldbuild-standalone"' in spec


def test_old_app_environment_does_not_redirect_independent_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("FIELDBUILD_STANDALONE_APP_DATA_DIR", raising=False)
    monkeypatch.setenv("QFIELD_BUILDER_APP_DATA_DIR", str(tmp_path / "old-app"))
    assert _real_app_data_dir().name == "FieldBuild Standalone"
    independent_dir = tmp_path / "independent-app"
    monkeypatch.setenv("FIELDBUILD_STANDALONE_APP_DATA_DIR", str(independent_dir))
    assert _real_app_data_dir() == independent_dir


def test_application_startup_never_migrates_old_credentials(monkeypatch):
    class FakeApplication:
        def exec(self):
            return 0

    class FakeWizard:
        def show(self):
            pass

    def forbidden():
        raise AssertionError("Independent startup must not migrate another app's credentials")

    monkeypatch.setattr(app, "QApplication", lambda argv: FakeApplication())
    monkeypatch.setattr(app, "_apply_flat_modern_style", lambda instance: None)
    monkeypatch.setattr(app, "maybe_prompt_for_first_launch_password", lambda: None)
    monkeypatch.setattr(app, "ProjectBuilderWizard", FakeWizard)
    monkeypatch.setattr(credential_store, "migrate_legacy_credentials", forbidden)
    assert app.main(["fieldbuild-standalone"]) == 0
