import logging
from pathlib import Path

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx import addnodes
from sphinx.util.docutils import SphinxDirective

from .scanner import DirectoryTree, normalize_source_suffixes, scan_directory_tree

logger = logging.getLogger(__name__)


class RGlobToctreeDirective(SphinxDirective):
    """ディレクトリ階層を nested bullet list + hidden toctree として出力"""

    has_content = False
    option_spec = {
        "root": directives.unchanged_required,
        "maxdepth": directives.nonnegative_int,
        "recurse-depth": directives.nonnegative_int,
        "caption": directives.unchanged,
        "hidden": directives.flag,
        "numbered": directives.unchanged,
        "reversed": directives.flag,
        "titlesonly": directives.flag,
    }

    def run(self) -> list[nodes.Node]:
        root_rel = self.options.get("root", ".")
        srcdir = Path(self.env.srcdir)

        # srcdir からの相対パスとして解決 (ドキュメント位置に依存しない)
        root_abs = srcdir / root_rel

        # srcdir 範囲チェック (symlink/.. 対策)
        try:
            root_from_src = root_abs.resolve().relative_to(srcdir.resolve())
        except ValueError:
            logger.warning(
                "rglob-toctree: root %r resolves outside srcdir, skipping",
                root_rel,
            )
            return []

        if not root_abs.is_dir():
            logger.warning(
                "rglob-toctree: root %r is not a directory",
                root_rel,
            )
            return []

        suffixes = normalize_source_suffixes(self.env.config.source_suffix)
        recurse_depth = self.options.get("recurse-depth", 0)
        tree = scan_directory_tree(srcdir, str(root_from_src), suffixes, recurse_depth)

        flat_docs = _collect_all_docs(tree)

        if "reversed" in self.options:
            flat_docs.reverse()

        result_nodes: list[nodes.Node] = []

        # :hidden: 指定時は bullet list を省略
        if "hidden" not in self.options:
            bullet = _build_bullet_list(
                tree, "reversed" in self.options, self.env.docname
            )
            if bullet is not None:
                result_nodes.append(bullet)

        if flat_docs:
            result_nodes.append(self._build_toctree(flat_docs))

        return result_nodes

    def _build_toctree(self, docnames: list[str]) -> addnodes.toctree:
        toctree = addnodes.toctree()
        toctree["entries"] = [(None, dn) for dn in docnames]
        toctree["includefiles"] = list(docnames)
        toctree["maxdepth"] = self.options.get("maxdepth", -1)
        toctree["hidden"] = True
        toctree["caption"] = self.options.get("caption")
        toctree["titlesonly"] = "titlesonly" in self.options
        toctree["glob"] = False
        toctree["parent"] = self.env.docname

        # :numbered: の型正規化 (flag → 0/1, int → そのまま)
        numbered_raw = self.options.get("numbered", 0)
        if numbered_raw is None:
            # flag 指定 (値なし) → True 相当
            toctree["numbered"] = 1
        elif isinstance(numbered_raw, str) and numbered_raw.isdigit():
            toctree["numbered"] = int(numbered_raw)
        else:
            toctree["numbered"] = 0

        return toctree


def _make_doc_xref(docname: str, text: str, refdoc: str) -> addnodes.pending_xref:
    """std:doc 相当の cross-reference ノードを生成"""
    ref = addnodes.pending_xref(
        "",
        refdomain="std",
        reftype="doc",
        reftarget=f"/{docname}",
        refdoc=refdoc,
        refexplicit=True,
        refwarn=True,
    )
    ref += nodes.inline("", text)
    return ref


def _collect_all_docs(tree: DirectoryTree) -> list[str]:
    """ツリー内の全ドキュメント docname をフラットに収集"""
    result: list[str] = []
    result.extend(tree["files"])
    for _name, subtree in sorted(tree["dirs"].items()):
        result.extend(_collect_all_docs(subtree))
    return result


def _build_bullet_list(
    tree: DirectoryTree, reverse: bool, refdoc: str
) -> nodes.bullet_list | None:
    """再帰的に nested bullet list を構築"""
    items: list[nodes.list_item] = []

    # ディレクトリエントリ
    dir_entries = sorted(tree["dirs"].items(), reverse=reverse)
    for name, subtree in dir_entries:
        item = nodes.list_item()
        para = nodes.paragraph("", "", nodes.strong("", name))
        item += para

        child_list = _build_bullet_list(subtree, reverse, refdoc)
        if child_list is not None:
            item += child_list
        items.append(item)

    # ファイルエントリ
    file_entries = sorted(tree["files"], reverse=reverse)
    for docname in file_entries:
        item = nodes.list_item()
        # ファイル名部分のみ表示 (パスの最後のセグメント)
        display_name = docname.rsplit("/", 1)[-1]
        para = nodes.paragraph("", "", _make_doc_xref(docname, display_name, refdoc))
        item += para
        items.append(item)

    if not items:
        return None

    blist = nodes.bullet_list()
    blist.extend(items)
    return blist
