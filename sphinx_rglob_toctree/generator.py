import logging
from pathlib import Path

from .scanner import (
    DirectoryTree,
    has_physical_index,
    scan_directory_tree,
)

logger = logging.getLogger(__name__)


def generate_stubs(
    srcdir: Path,
    root: str,
    suffixes: list[str],
    recurse_depth: int = 0,
) -> list[Path]:
    """root 配下の中間ディレクトリにスタブ index を生成する

    既に index ファイルが存在するディレクトリはスキップ。
    """
    tree = scan_directory_tree(srcdir, root, suffixes, recurse_depth)
    suffix = suffixes[0]
    generated: list[Path] = []

    # root 自体に index がなければスタブ生成
    if not has_physical_index(srcdir / root, suffixes):
        children = _collect_children_for_stub(tree)
        if children:
            content = _make_stub_content(Path(root).name, children, suffix)
            stub_path = srcdir / root / f"index{suffix}"
            stub_path.write_text(content, encoding="utf-8")
            generated.append(stub_path)

    _generate_recursive(srcdir, root, tree, suffix, suffixes, generated)
    return generated


def _generate_recursive(
    srcdir: Path,
    prefix: str,
    tree: DirectoryTree,
    suffix: str,
    suffixes: list[str],
    generated: list[Path],
) -> None:
    for dirname, subtree in sorted(tree["dirs"].items()):
        dir_path = f"{prefix}/{dirname}"

        if not has_physical_index(srcdir / dir_path, suffixes):
            children = _collect_children_for_stub(subtree)
            if children:
                content = _make_stub_content(dirname, children, suffix)
                stub_path = srcdir / dir_path / f"index{suffix}"
                stub_path.write_text(content, encoding="utf-8")
                generated.append(stub_path)

        _generate_recursive(srcdir, dir_path, subtree, suffix, suffixes, generated)


def _collect_children_for_stub(tree: DirectoryTree) -> list[str]:
    """スタブの toctree に記載する子エントリ (相対パス) を収集"""
    children: list[str] = []
    for child_dir in sorted(tree["dirs"].keys()):
        children.append(f"{child_dir}/index")
    for docname in sorted(tree["files"]):
        # docname はフルパス (e.g. "plans/2026/03/24/spam")
        # スタブからの相対パスはファイル名部分のみ
        children.append(docname.rsplit("/", 1)[-1])
    return children


def _make_stub_content(title: str, children: list[str], suffix: str) -> str:
    """スタブ index のコンテンツを生成 (MyST / RST 対応)"""
    entries = "\n".join(children)

    if suffix in (".md",):
        return f"# {title}\n\n```{{toctree}}\n:hidden:\n\n{entries}\n```\n"

    # RST format
    underline = "=" * len(title)
    indent = "\n".join(f"   {c}" for c in children)
    return f"{title}\n{underline}\n\n.. toctree::\n   :hidden:\n\n{indent}\n"


def save_manifest(manifest_path: Path, generated: list[Path]) -> None:
    """生成したスタブのパスをマニフェストに保存"""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        "\n".join(str(p) for p in generated) + "\n",
        encoding="utf-8",
    )


def cleanup_stubs(manifest_path: Path) -> None:
    """マニフェストに記録されたスタブを削除し、空ディレクトリも掃除"""
    if not manifest_path.exists():
        return

    lines = manifest_path.read_text(encoding="utf-8").strip().splitlines()
    # 子から先に削除するため逆順ソート
    for line in sorted(lines, reverse=True):
        p = Path(line)
        if p.exists():
            p.unlink()
            logger.debug("rglob-toctree: removed stub %s", p)

    # 空ディレクトリの掃除 (子→親の順)
    dirs_to_check = sorted({Path(line).parent for line in lines}, reverse=True)
    for d in dirs_to_check:
        try:
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()
                logger.debug("rglob-toctree: removed empty dir %s", d)
        except OSError:
            pass

    manifest_path.unlink(missing_ok=True)
