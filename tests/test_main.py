import pytest

import idle_runner.__main__ as main_module


def test_invalid_config_is_reported_cleanly(tmp_path, capsys) -> None:
    config = tmp_path / "config.toml"
    config.write_text("[general]\nbogus = 1\n")

    assert main_module.main(["run", "--config", str(config)]) == 1
    assert "unknown setting 'bogus'" in capsys.readouterr().err


def test_runtime_value_errors_are_not_reported_as_config_errors(tmp_path, monkeypatch) -> None:
    config = tmp_path / "config.toml"
    config.write_text("")
    monkeypatch.chdir(tmp_path)  # logs/ is created relative to the working directory

    def broken_backend(name: str) -> None:
        raise ValueError("cannot reshape array")

    monkeypatch.setattr(main_module, "X11Backend", broken_backend)
    with pytest.raises(ValueError, match="cannot reshape"):
        main_module.main(["run", "--config", str(config)])
