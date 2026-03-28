from __future__ import annotations

from typing import TYPE_CHECKING

from .directive import RGlobToctreeDirective

if TYPE_CHECKING:
    from sphinx.application import Sphinx


def setup(app: Sphinx) -> dict[str, object]:
    app.add_config_value("rglob_toctree_title_format", "{path}", "env", types=[str])
    app.add_directive("rglob-toctree", RGlobToctreeDirective)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
