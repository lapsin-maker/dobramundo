"""Monta downloads verificáveis a partir dos dois builds aprovados pela CI.

Não publica no GitHub. A mesma rotina serve a qualquer versão; o manifesto
liga os arquivos à árvore Git testada, sem depender de pastas do autor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional

from packaging.version import InvalidVersion, Version

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.8 in the supported CI matrix
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dobramundo import __version__  # noqa: E402
from tools.build_cartridge import DESKTOP_ONLY, MANIFEST  # noqa: E402
from tools.runtime_assets import runtime_assets  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unique(root: Path, pattern: str) -> Path:
    files = list(root.rglob(pattern))
    if len(files) != 1:
        raise ValueError(f"Esperava um {pattern} em {root}, encontrei {len(files)}")
    return files[0]


def verified_build(
    root: Path,
    expected_commit: Optional[str] = None,
    expected_ci_run_id: Optional[str] = None,
    expected_ci_attempt: Optional[str] = None,
) -> dict:
    report = json.loads(unique(root, "self_test.json").read_text(encoding="utf-8"))
    if report.get("status") != "ok" or report.get("camera", {}).get("detector") != "ok":
        raise ValueError("O pacote precisa de self-test aprovado incluindo detector")
    if report.get("versao") != __version__:
        raise ValueError("A versão do executável não corresponde à versão da release")
    if not report.get("run_id"):
        raise ValueError("Relatório de build sem identificador de execução")
    if expected_commit and (
        report.get("build_commit") != expected_commit or report.get("github_sha") != expected_commit
    ):
        raise ValueError("O commit do executável não corresponde ao commit aprovado pela CI")
    if expected_ci_run_id and report.get("github_run_id") != expected_ci_run_id:
        raise ValueError("A execução de CI do executável não corresponde ao relatório aprovado")
    if expected_ci_attempt and report.get("github_run_attempt") != expected_ci_attempt:
        raise ValueError("A tentativa de CI do executável não corresponde ao relatório aprovado")
    return report


def portable_sources(root: Path) -> Dict[str, Path]:
    """Map source files copied into the cartucho by build_cartridge.stage()."""
    package_root = root / "dobramundo"
    result = {}
    for path in package_root.rglob("*.py"):
        relative = path.relative_to(package_root).as_posix()
        if relative in DESKTOP_ONLY or "__pycache__" in path.parts:
            continue
        result["dobramundo/" + relative] = path
    return result


def github_run_id(ci_report: dict) -> Optional[str]:
    for key in ("databaseId", "runId", "run_id", "id", "github_run_id"):
        value = ci_report.get(key)
        if value is not None and str(value):
            return str(value)
    url = ci_report.get("url", "")
    match = re.search(r"/actions/runs/(\d+)(?:/|$)", url)
    return match.group(1) if match else None


def github_run_attempt(ci_report: dict) -> Optional[str]:
    for key in ("runAttempt", "run_attempt", "attempt", "github_run_attempt"):
        value = ci_report.get(key)
        if value is not None and str(value):
            return str(value)
    return None


def assert_tracked_inputs(paths: List[Path], root: Path = ROOT) -> None:
    tracked = set(
        subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
        .decode("utf-8", errors="surrogateescape")
        .split("\0")
    )
    missing = sorted(
        path.relative_to(root).as_posix() for path in paths if path.relative_to(root).as_posix() not in tracked
    )
    if missing:
        raise ValueError("Entradas do pacote não rastreadas pelo commit: " + ", ".join(missing[:8]))


def assert_clean_checkout(root: Path = ROOT) -> None:
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip()
    if status:
        raise ValueError("A árvore de trabalho contém alterações fora do commit da release")


def validate_cartridge_sources(archive: zipfile.ZipFile, root: Path) -> None:
    expected = portable_sources(root)
    names = archive.namelist()
    if len(names) != len(set(names)):
        raise ValueError("Cartucho contém caminhos duplicados")
    actual = {name for name in names if name.startswith("dobramundo/") and name.endswith(".py")}
    if actual != set(expected):
        missing = sorted(set(expected) - actual)
        extra = sorted(actual - set(expected))
        raise ValueError(
            f"Fontes portáteis do cartucho diferem do inventário: faltando={missing[:6]} excedentes={extra[:6]}"
        )
    for name, source in expected.items():
        if archive.read(name) != source.read_bytes():
            raise ValueError("Código do cartucho difere da árvore validada: " + name)


def write_batch(path: Path, content: str) -> None:
    """Write Windows launchers with CRLF even when packaging on Linux."""
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    path.write_bytes(normalized.replace("\n", "\r\n").encode("ascii"))


def _unique_manifest_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Chave duplicada no manifesto: " + key)
        result[key] = value
    return result


def validate_cartridge_manifest(archive: zipfile.ZipFile, expected_commit: str) -> dict:
    """Check the built manifest emitted by TSDK, not the authored ttea.toml."""
    if archive.namelist().count("manifest.json") != 1:
        raise ValueError("Cartucho precisa de um manifest.json único na raiz")
    if archive.getinfo("manifest.json").file_size > 1024 * 1024:
        raise ValueError("Manifesto do cartucho excede 1 MiB")
    manifest = json.loads(archive.read("manifest.json"), object_pairs_hook=_unique_manifest_object)
    if not isinstance(manifest, dict):
        raise ValueError("Manifesto do cartucho precisa ser um objeto")
    if manifest.get("version") != __version__:
        raise ValueError("A versão do cartucho difere da release")
    authored = tomllib.loads(MANIFEST)["game"]
    if set(manifest) != set(authored) | {"format_version", "builder", "build"}:
        raise ValueError("Campos do manifesto diferem do contrato de autoria")
    # Compare the entire authored contract, including nested value types, without
    # duplicating TSDK's general-purpose schema or our project's metadata.
    actual_authored = {key: manifest[key] for key in authored}
    if json.dumps(actual_authored, sort_keys=True) != json.dumps(authored, sort_keys=True):
        raise ValueError("Identidade ou formato do cartucho incompatível")
    if type(manifest["format_version"]) is not int or manifest["format_version"] != 1:
        raise ValueError("Formato do cartucho incompatível")
    builder = manifest["builder"]
    if not isinstance(builder, dict) or set(builder) != {"version"} or not isinstance(builder["version"], str):
        raise ValueError("Builder do cartucho inválido")
    try:
        Version(builder["version"])
    except InvalidVersion as exc:
        raise ValueError("Versão do builder inválida") from exc
    build = manifest.get("build")
    if (
        not isinstance(build, dict)
        or set(build) != {"source_commit", "dirty"}
        or build["source_commit"] != expected_commit
        or build["dirty"] is not False
    ):
        raise ValueError("Cartucho precisa vir do commit da release, sem alterações locais")
    return manifest


def validate_tar(path: Path) -> None:
    with tarfile.open(path, "r:gz") as archive:
        executable = archive.getmember("Dobramundo/Dobramundo")
        if not executable.mode & 0o111:
            raise ValueError("Executável Linux sem permissão de execução")
        for member in archive.getmembers():
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts:
                raise ValueError("Caminho inseguro no pacote Linux")
            if member.issym() or member.islnk():
                link = PurePosixPath(member.linkname)
                base = name.parent if member.issym() else PurePosixPath()
                resolved = PurePosixPath(posixpath.normpath(str(base / link)))
                if link.is_absolute() or not resolved.parts or resolved.parts[0] != "Dobramundo":
                    raise ValueError("Link inseguro no pacote Linux")


def tree(revision: str) -> str:
    return subprocess.check_output(["git", "rev-parse", revision + "^{tree}"], cwd=ROOT, text=True).strip()


def package(args) -> dict:
    ci = json.loads(args.ci_report.read_text(encoding="utf-8-sig"))
    if ci.get("status") != "completed" or ci.get("conclusion") != "success":
        raise ValueError("A execução de CI precisa estar concluída e aprovada")
    if not ci.get("jobs") or any(job.get("conclusion") != "success" for job in ci["jobs"]):
        raise ValueError("Todos os jobs da execução completa precisam ter passado")
    if ci.get("headSha") != args.build_commit:
        raise ValueError("O commit da CI não corresponde ao build informado")
    if tree(args.build_commit) != tree(args.release_commit):
        raise ValueError("A árvore da release difere da árvore validada")
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != args.release_commit:
        raise ValueError("Execute na revisão da release para resolver a versão corretamente")
    assert_clean_checkout(ROOT)
    ci_run = github_run_id(ci)
    if ci_run is None:
        raise ValueError("Relatório da CI sem identificador de execução")
    ci_attempt = github_run_attempt(ci)
    windows_report = verified_build(args.windows, args.build_commit, ci_run, ci_attempt)
    linux_report = verified_build(args.linux, args.build_commit, ci_run, ci_attempt)
    if windows_report.get("run_id") == linux_report.get("run_id"):
        raise ValueError("Builds Windows e Linux têm o mesmo identificador de execução local")
    if not windows_report.get("github_run_attempt") or windows_report.get("github_run_attempt") != linux_report.get(
        "github_run_attempt"
    ):
        raise ValueError("Builds Windows e Linux não pertencem à mesma tentativa de CI")
    windows = unique(args.windows, "Dobramundo.exe").parent
    if not (windows / "_internal").is_dir():
        raise ValueError("O diretório _internal precisa acompanhar o executável")
    linux_tar = unique(args.linux, "Dobramundo-Linux.tar.gz")
    validate_tar(linux_tar)
    with zipfile.ZipFile(args.cartridge) as archive:
        if archive.testzip() is not None:
            raise ValueError("Cartucho incompleto ou corrompido")
        validate_cartridge_manifest(archive, args.release_commit)
        validate_cartridge_sources(archive, ROOT)
        asset_records = list(runtime_assets(ROOT, console=True))
        expected_asset_names = {"assets/" + relative.as_posix() for _source, relative in asset_records}
        actual_asset_names = {
            name for name in archive.namelist() if name.startswith("assets/") and not name.endswith("/")
        }
        if actual_asset_names != expected_asset_names:
            missing = sorted(expected_asset_names - actual_asset_names)
            extra = sorted(actual_asset_names - expected_asset_names)
            raise ValueError(f"Assets do cartucho diferem do inventário: faltando={missing[:6]} excedentes={extra[:6]}")
        assert_tracked_inputs([*portable_sources(ROOT).values(), *(source for source, _relative in asset_records)])
        for source, relative in asset_records:
            if archive.read("assets/" + relative.as_posix()) != source.read_bytes():
                raise ValueError("Asset do cartucho difere do inventário: " + str(relative))
    args.out.mkdir(parents=True, exist_ok=True)
    write_batch(
        windows / "Jogar-Dobramundo.bat",
        '@echo off\nsetlocal\ncd /d "%~dp0"\n"%~dp0Dobramundo.exe" %*\n',
    )
    write_batch(
        windows / "Continuar-perfil-1.5.bat",
        '@echo off\nsetlocal\ncd /d "%~dp0"\n'
        'if not exist "%LOCALAPPDATA%\\Dobramundo-1.5.0" (\n'
        " echo Perfil anterior nao encontrado. Use Jogar-Dobramundo.bat.\n pause\n exit /b 1\n)\n"
        'set "DOBRAMUNDO_DATA_DIR=%LOCALAPPDATA%\\Dobramundo-1.5.0"\n"%~dp0Dobramundo.exe" %*\n',
    )
    (windows / "LEIA-ME.txt").write_text(
        f"Dobramundo {__version__}\n\nExtraia toda a pasta e abra Jogar-Dobramundo.bat.\n"
        "Mantenha _internal junto do jogo. Nao precisa instalar Python.\n"
        "Pilotos locais: %APPDATA%\\Dobramundo. A webcam e processada no computador.\n"
        "Ajuste movimento, tempo e conforto nas Opcoes com acompanhamento.\n"
        "Se usou o lancador 1.5, o atalho Continuar-perfil-1.5 abre a pasta antiga.\n",
        encoding="utf-8",
    )
    files = []
    win_zip = args.out / f"Dobramundo-{__version__}-Windows.zip"
    with zipfile.ZipFile(win_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(windows.rglob("*")):
            if path.is_file():
                if path.name in {"dobramundo_perfil.json", "perfis.json", "dobramundo.log"}:
                    raise ValueError("Dados de usuário encontrados no pacote")
                archive.write(path, f"Dobramundo-{__version__}-Windows/" + path.relative_to(windows).as_posix())
    with zipfile.ZipFile(win_zip) as archive:
        if archive.testzip() is not None:
            raise ValueError("Falha de integridade no ZIP Windows")
    files.append(win_zip)
    for source, name in (
        (linux_tar, f"Dobramundo-{__version__}-Linux.tar.gz"),
        (args.cartridge, f"dobramundo-{__version__}.ttea"),
    ):
        target = args.out / name
        shutil.copy2(source, target)
        files.append(target)
    if args.gallery:
        gallery = args.out / f"Dobramundo-{__version__}-Galeria.zip"
        with zipfile.ZipFile(gallery, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(args.gallery.rglob("*")):
                if path.is_file() and path.suffix in {".png", ".html", ".gif"}:
                    archive.write(path, path.relative_to(args.gallery).as_posix())
        files.append(gallery)
    manifest = {
        "version": __version__,
        "release_commit": args.release_commit,
        "desktop_build_commit": args.build_commit,
        "source_tree": tree(args.release_commit),
        "build_ci": ci.get("url"),
        "build_ci_run_id": ci_run,
        "build_ci_run_attempt": ci_attempt,
        "validation": {"windows": windows_report, "linux": linux_report},
        "physical_acceptance": "separate; see docs/VALIDACAO_PRESENCIAL.md",
        "artifacts": [{"file": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)} for path in files],
    }
    manifest_path = args.out / "release-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    files.append(manifest_path)
    (args.out / "SHA256SUMS.txt").write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in files), encoding="ascii"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("windows", "linux", "cartridge", "ci-report", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--build-commit", required=True)
    parser.add_argument("--release-commit", required=True)
    parser.add_argument("--gallery", type=Path)
    manifest = package(parser.parse_args())
    print(json.dumps(manifest["artifacts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
