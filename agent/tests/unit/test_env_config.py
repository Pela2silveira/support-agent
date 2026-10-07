from pathlib import Path

from diag.config import load_env


def test_load_env_reads_secret_values(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "PACS_ORTHANC_HOST=10.20.10.20\n"
        "DICOM_SERVER_HOST=10.20.10.21\n",
        encoding="utf-8",
    )

    data = load_env(env_file)

    assert data["PACS_ORTHANC_HOST"] == "10.20.10.20"
    assert data["DICOM_SERVER_HOST"] == "10.20.10.21"
