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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dobramundo import __version__  # noqa: E402
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


def verified_build(root: Path) -> dict:
    report = json.loads(unique(root, "self_test.json").read_text(encoding="utf-8"))
    if report.get("status") != "ok" or report.get("camera", {}).get("detector") != "ok":
        raise ValueError("O pacote precisa de self-test aprovado incluindo detector")
    return report


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
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True).strip():
        raise ValueError("A árvore de trabalho contém alterações fora do commit da release")
    windows_report, linux_report = verified_build(args.windows), verified_build(args.linux)
    windows = unique(args.windows, "Dobramundo.exe").parent
    if not (windows / "_internal").is_dir():
        raise ValueError("O diretório _internal precisa acompanhar o executável")
    linux_tar = unique(args.linux, "Dobramundo-Linux.tar.gz")
    validate_tar(linux_tar)
    with zipfile.ZipFile(args.cartridge) as archive:
        if archive.testzip() is not None or "ttea.toml" not in archive.namelist():
            raise ValueError("Cartucho incompleto ou corrompido")
        manifest_text = archive.read("ttea.toml").decode("utf-8")
        if re.search(r'^version\s*=\s*"' + re.escape(__version__) + r'"\s*$', manifest_text, re.MULTILINE) is None:
            raise ValueError("A versão do cartucho difere da release")
        for name in archive.namelist():
            if name.startswith("dobramundo/") and name.endswith(".py"):
                source = ROOT / name
                if not source.is_file() or archive.read(name) != source.read_bytes():
                    raise ValueError("Código do cartucho difere da árvore validada: " + name)
        for source, relative in runtime_assets(ROOT, console=True):
            if archive.read("assets/" + relative.as_posix()) != source.read_bytes():
                raise ValueError("Asset do cartucho difere do inventário: " + str(relative))
    args.out.mkdir(parents=True, exist_ok=True)
    (windows / "Jogar-Dobramundo.bat").write_text(
        '@echo off\nsetlocal\ncd /d "%~dp0"\n"%~dp0Dobramundo.exe" %*\n', encoding="ascii"
    )
    (windows / "Continuar-perfil-1.5.bat").write_text(
        '@echo off\nsetlocal\ncd /d "%~dp0"\n'
        'if not exist "%LOCALAPPDATA%\\Dobramundo-1.5.0" (\n'
        " echo Perfil anterior nao encontrado. Use Jogar-Dobramundo.bat.\n pause\n exit /b 1\n)\n"
        'set "DOBRAMUNDO_DATA_DIR=%LOCALAPPDATA%\\Dobramundo-1.5.0"\n"%~dp0Dobramundo.exe" %*\n',
        encoding="ascii",
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
