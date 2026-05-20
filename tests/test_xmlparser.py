import pathlib
from copy import deepcopy

from lxml.etree import Element
from xmlparser.xmlparser import (
    ArticleMeta,
    chars,
    copy_curies,
    curies,
    fromstring,
    merge_children,
    parse,
    parse_pubmed_article,
    promote_spans,
    reinsert_tags,
    remove_tags,
    replace_annotation,
    tostring,
)

TESTS_DIR = pathlib.Path(__file__).parent
DATA_DIR = TESTS_DIR / "data"


def load(name: str) -> str:
    """Return the XML fixture ``tests/data/<name>`` without its trailing newline."""
    return (DATA_DIR / name).read_text(encoding="utf-8").rstrip("\n")


tryptophan = "<div>with the indole precursor <sc>l</sc>-tryptophan, we observed</div>"
italic = (
    "<div>with the <italic>indole precursor l-tryptophan</italic>, we observed</div>"
)
spaced_tag_string = (
    '<sec id="s4.12"><title>CE-ESI-TOF-MS target analysis.</title></sec>'
)
spanseq = (
    '<root><italic><span resource="#T3" typeof="d3o:Strain">P</span></italic>'
    '<span resource="#T3" typeof="d3o:Strain">2</span>'
    '<sub><span resource="#T3" typeof="d3o:Strain">1</span></sub></root>'
)
spanlifted = (
    '<root><span resource="#T3" typeof="d3o:Strain"><italic>P</italic></span>'
    '<span resource="#T3" typeof="d3o:Strain">2</span>'
    '<span resource="#T3" typeof="d3o:Strain"><sub>1</sub></span></root>'
)


def test_copy_curies():
    empty = Element("div")

    another_empty = deepcopy(empty)

    first = Element(
        "div",
        attrib={"prefix": "d3o: https://purl.dsmz.de/schema/"},
    )
    target1 = Element(
        "div",
        attrib={"prefix": "schema: http://schema.org/ dc: http://purl.org/dc/terms/"},
    )
    target2 = Element(
        "div",
        attrib={
            "prefix": (
                "schema: http://schema.org/ dc: http://purl.org/dc/terms/ "
                "d3o: https://purl.dsmz.de/schema/"
            )
        },
    )

    copy_curies(source=first, target=target1)
    assert curies(target1) == curies(target2)

    copy_curies(source=target1, target=first)
    assert curies(first) == curies(target2)

    assert tostring(empty, method="c14n2") == tostring(another_empty, method="c14n2")

    copy_curies(source=empty, target=first)
    assert tostring(empty, method="c14n2") == tostring(another_empty, method="c14n2")

    assert curies(first) == curies(target2)

    copy_curies(source=empty, target=another_empty)

    assert tostring(empty, method="c14n2") == tostring(another_empty, method="c14n2")


def test_extract_curies():
    div = Element(
        "div",
        attrib={
            "prefix": (
                "schema: http://schema.org/ dc: http://purl.org/dc/terms/ "
                "d3o: https://purl.dsmz.de/schema/"
            )
        },
    )

    assert curies(div) == {
        "schema: http://schema.org/",
        "dc: http://purl.org/dc/terms/",
        "d3o: https://purl.dsmz.de/schema/",
    }


def test_non_tag_chars_iterator_works() -> None:
    assert list(chars("precursor <sc>l</sc>-tryptophan")) == [
        "p",
        "r",
        "e",
        "c",
        "u",
        "r",
        "s",
        "o",
        "r",
        " ",
        "<sc>l</sc>",
        "-",
        "t",
        "r",
        "y",
        "p",
        "t",
        "o",
        "p",
        "h",
        "a",
        "n",
    ]


def test_remove_and_reinsert_tags_are_inverses() -> None:
    assert reinsert_tags(remove_tags(tryptophan), tryptophan) == tryptophan
    assert (
        reinsert_tags(remove_tags(spaced_tag_string), spaced_tag_string)
        == spaced_tag_string
    )


def test_remove_and_insert_with_annotation_is_valid_html() -> None:
    annotated_tryptophan = (
        "with the indole precursor "
        '<span typeof="entity">l</span>-tryptophan, we observed'
    )
    expected_tryptophan = (
        "<div>with the indole precursor "
        '<sc><span typeof="entity">l</span></sc>-tryptophan, we observed</div>'
    )
    assert reinsert_tags(annotated_tryptophan, tryptophan) == expected_tryptophan

    annotated_italic = (
        'with the indole precursor <span typeof="entity">'
        "l-tryptophan</span>, we observed"
    )
    expected_italic = (
        "<div>with the <italic>indole precursor "
        '<span typeof="entity">l-tryptophan</span></italic>, we observed</div>'
    )
    assert reinsert_tags(annotated_italic, italic) == expected_italic


def test_reinsert_tags_preserves_outer_div():
    for case in ("case1", "case2"):
        original = load(f"reinsert/{case}.original.xml")
        serialized = load(f"reinsert/{case}.serialized.xml")
        goal = load(f"reinsert/{case}.goal.xml")
        assert reinsert_tags(serialized, original) == goal


def test_div_with_attribs():
    div = (
        '<div prefix="d3o: https://purl.dsmz.de/schema/"> '
        "Crystallization and preliminary X-ray diffraction analysis of two N-terminal "
        "fragments of the DNA-cleavage domain of topoisomerase IV from <span"
        ' resource="#T1" typeof="d3o:Bacteria">Staphylococcus aureus</span>'
    )
    assert next(chars(div)) == '<div prefix="d3o: https://purl.dsmz.de/schema/"> '


def test_spans_to_the_top():
    tree = fromstring(spanseq)
    assert tostring(promote_spans(tree), encoding="unicode") == spanlifted


def test_cousin_spans_should_be_merged_when_possible():
    tree = fromstring(spanlifted)
    assert (
        tostring(merge_children(tree), encoding="unicode")
        == '<root><span resource="#T3" typeof="d3o:Strain"><italic>P</italic>2<sub>1</sub></span></root>'
    )


def test_replace_annotation():
    og = load("replace_annotation.og.xml")
    annotation = load("replace_annotation.annotation.xml")
    expected = load("replace_annotation.expected.xml")
    assert replace_annotation(og, annotation) == expected


def test_parse_pubmed_article():
    tree = parse(str(DATA_DIR / "pubmed_30562557.xml"))
    record = tree.xpath("//PubmedArticle")[0]
    article = parse_pubmed_article(record)

    assert isinstance(article.meta, ArticleMeta)
    assert article.meta.title == "Endometriosis and cancer."
    assert article.meta.authors == (
        "Kajiyama, Hiroaki; Suzuki, Shiro; Yoshihara, Masato; Tamauchi, Satoshi; "
        "Yoshikawa, Nobuhisa; Niimi, Kaoru; Shibata, Kiyosumi; Kikkawa, Fumitaka"
    )
    assert article.meta.journal == "Free radical biology & medicine"
    assert article.meta.volume == "133"
    assert article.meta.number is None
    assert article.meta.pages == "186-192"
    assert article.meta.year == 2019
    assert article.body is None
    assert article.abstract is not None
    assert article.abstract.startswith("Endometriosis, characterized by")
