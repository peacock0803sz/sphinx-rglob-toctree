from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TypedDict

from sphinx.errors import ExtensionError


class DirectoryTree(TypedDict):
    dirs: dict[str, DirectoryTree]
    files: list[str]


def normalize_source_suffixes(value: Any) -> list[str]:
    """source_suffix の全形式 (str | list | dict) を list[str] に正規化"""
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [str(k) for k in value.keys()]
    if isinstance(value, Sequence):
        return [str(v) for v in value]
    raise ExtensionError(f"Unsupported source_suffix type: {value!r}")


def has_physical_index(dir_path: Path, source_suffixes: list[str]) -> bool:
    """いずれかの source_suffix で index.* が存在するか"""
    return any((dir_path / f"index{sfx}").exists() for sfx in source_suffixes)


def _is_doc_file(path: Path, source_suffixes: list[str]) -> bool:
    return path.is_file() and path.suffix in source_suffixes


def _path_to_docname(path: Path, srcdir: Path) -> str:
    """物理パスを Sphinx docname (拡張子なし, / 区切り) に変換"""
    rel = path.relative_to(srcdir)
    return str(rel.with_suffix("")).replace("\\", "/")


def scan_directory_tree(
    srcdir: Path,
    root: str,
    source_suffixes: list[str],
    recurse_depth: int = 0,
) -> DirectoryTree:
    """
    ディレクトリツリーを走査し、階層構造を返す。

    Args:
        srcdir: Sphinx ソースディレクトリ (絶対パス)
        root: srcdir からの相対パス
        source_suffixes: 対象ファイル拡張子 (例: [".md", ".rst"])
        recurse_depth: 再帰の深さ制限 (0 = 無制限)

    Returns:
        DirectoryTree: {"dirs": {name: subtree}, "files": [docname, ...]}
        files は拡張子なしの docname。空ディレクトリは含めない。
    """
    root_abs = srcdir / root
    return _scan_recursive(root_abs, srcdir, source_suffixes, recurse_depth, 1)


def _scan_recursive(
    current: Path,
    srcdir: Path,
    suffixes: list[str],
    max_depth: int,
    current_depth: int,
) -> DirectoryTree:
    dirs: dict[str, DirectoryTree] = {}
    files: list[str] = []

    if not current.is_dir():
        return {"dirs": dirs, "files": files}

    for entry in sorted(current.iterdir()):
        if entry.name.startswith(".") or entry.name.startswith("_"):
            continue

        if entry.is_dir():
            if max_depth != 0 and current_depth >= max_depth:
                continue
            subtree = _scan_recursive(
                entry, srcdir, suffixes, max_depth, current_depth + 1
            )
            # 空ディレクトリは含めない
            if subtree["dirs"] or subtree["files"]:
                dirs[entry.name] = subtree

        elif _is_doc_file(entry, suffixes):
            # index ファイルはスキップ (has_physical_index で別途判定)
            if entry.stem == "index":
                continue
            files.append(_path_to_docname(entry, srcdir))

    return {"dirs": dirs, "files": files}
