import pytest
from docutils import nodes
from sphinx import addnodes


@pytest.mark.sphinx("html", testroot="basic")
def test_basic_hierarchy(app):
    """YYYY/MM/DD/*.md の階層 bullet list が生成される"""
    app.build()
    assert app.statuscode == 0

    # doctree を検証 (rglob-toctree は plans/index に配置)
    doctree = app.env.get_doctree("plans/index")
    bullet_lists = list(doctree.findall(nodes.bullet_list))
    assert len(bullet_lists) > 0, "bullet list が生成されていない"

    # toctree ノードが生成される
    # (resolve 前の doctree には addnodes.toctree が残る)
    content = (app.outdir / "plans/index.html").read_text()
    assert "ham" in content.lower()


@pytest.mark.sphinx("html", testroot="basic")
def test_toctree_has_immediate_children(app):
    """hidden toctree が直下の子 (中間 index) のみを含む"""
    app.build()
    doctree = app.env.get_doctree("plans/index")
    toctrees = list(doctree.findall(addnodes.toctree))
    assert len(toctrees) == 1, f"toctree が1つ必要だが {len(toctrees)} 個"

    toc = toctrees[0]
    includefiles = toc["includefiles"]
    # plans/index の直下には 2026/index のみ
    assert "plans/2026/index" in includefiles
    assert len(includefiles) == 1


@pytest.mark.sphinx("html", testroot="basic")
def test_bullet_list_structure(app):
    """bullet list がディレクトリ階層を反映する"""
    app.build()
    doctree = app.env.get_doctree("plans/index")

    # トップレベルの bullet list を取得
    top_bullets = list(doctree.findall(nodes.bullet_list))
    assert len(top_bullets) >= 1

    # "2026" ディレクトリが含まれる
    text = doctree.astext()
    assert "2026" in text


@pytest.mark.sphinx("html", testroot="basic")
@pytest.mark.parametrize(
    "href", ["2026/03/23/ham.html", "2026/03/24/spam.html", "2026/02/28/egg.html"]
)
def test_leaf_nodes_are_links(app, href):
    """bullet list のリーフノードが <a> リンクとして出力される"""
    app.build()
    content = (app.outdir / "plans/index.html").read_text()
    assert f'href="{href}"' in content


@pytest.mark.sphinx("html", testroot="basic")
def test_no_warnings(app, warning):
    """基本ビルドで警告が出ない"""
    app.build()
    warnings = warning.getvalue()
    # toctree 関連の警告がないことを確認
    assert "rglob-toctree" not in warnings


@pytest.mark.sphinx("html", testroot="basic")
@pytest.mark.parametrize(
    "page",
    [
        "plans/2026/index.html",
        "plans/2026/02/index.html",
        "plans/2026/02/28/index.html",
        "plans/2026/03/index.html",
        "plans/2026/03/23/index.html",
        "plans/2026/03/24/index.html",
    ],
)
def test_intermediate_pages_generated(app, page):
    """中間ディレクトリの stub ページが出力に含まれる"""
    app.build()
    assert (app.outdir / page).exists(), f"{page} が生成されていない"


@pytest.mark.sphinx("html", testroot="basic")
def test_stubs_cleaned_up_after_build(app):
    """ビルド後にソースツリーからスタブが削除される"""
    app.build()
    srcdir = app.srcdir
    # スタブは plans/2026/index.md 等に生成されるが、ビルド後に削除される
    stub_candidates = [
        srcdir / "plans" / "2026" / "index.md",
        srcdir / "plans" / "2026" / "03" / "index.md",
        srcdir / "plans" / "2026" / "03" / "24" / "index.md",
    ]
    for stub in stub_candidates:
        assert not stub.exists(), f"スタブが残留: {stub}"


@pytest.mark.sphinx("html", testroot="basic")
def test_existing_index_not_overwritten(app):
    """plans/index.md (ユーザー作成) が上書きされない"""
    app.build()
    content = (app.srcdir / "plans" / "index.md").read_text()
    assert "rglob-toctree" in content, "plans/index.md がスタブで上書きされた"
