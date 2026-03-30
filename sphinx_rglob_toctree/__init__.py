from pathlib import Path
from typing import TYPE_CHECKING

from .directive import RGlobToctreeDirective
from .generator import cleanup_stubs, generate_stubs, save_manifest
from .scanner import normalize_source_suffixes

if TYPE_CHECKING:
    from sphinx.application import Sphinx


def _manifest_path(app: Sphinx) -> Path:
    return Path(app.doctreedir) / "_rglob_stubs.manifest"


def _on_builder_inited(app: Sphinx) -> None:
    manifest = _manifest_path(app)
    # 前回ビルドの残留スタブを掃除 (中断対策)
    cleanup_stubs(manifest)

    roots: list[str] = app.config.rglob_toctree_roots
    if not roots:
        return

    srcdir = Path(app.srcdir)
    suffixes = normalize_source_suffixes(app.config.source_suffix)
    all_generated: list[Path] = []

    for root in roots:
        generated = generate_stubs(srcdir, root, suffixes)
        all_generated.extend(generated)

    if all_generated:
        save_manifest(manifest, all_generated)


def _on_build_finished(app: Sphinx, _exception: Exception | None) -> None:
    cleanup_stubs(_manifest_path(app))


def setup(app: Sphinx) -> dict[str, object]:
    app.add_config_value("rglob_toctree_title_format", "{path}", "env", types=[str])
    app.add_config_value("rglob_toctree_roots", [], "env", types=[list])
    app.add_directive("rglob-toctree", RGlobToctreeDirective)
    app.connect("builder-inited", _on_builder_inited)
    app.connect("build-finished", _on_build_finished)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
