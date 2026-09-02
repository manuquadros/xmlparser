"""Module providing tools for the manipulation of XML articles."""

import itertools
import re
from collections.abc import Iterator
from copy import deepcopy
from dataclasses import dataclass
from importlib import resources
from typing import NamedTuple, TypeGuard

from lxml.etree import (
    XSLT,
    Element,
    QName,
    XMLSyntaxError,
    XPathEvaluator,
    _Comment,
    _Element,
    _ElementTree,
    _ProcessingInstruction,
    cleanup_namespaces,
    fromstring,
    iterwalk,
    parse,
    register_namespace,
    tostring,
)
from nltk import RegexpTokenizer

XSLDIR = resources.files("xmlparser.stylesheets")

xml_char_tokenizer = RegexpTokenizer(r"<[\w/][^<>]*/?>|.")
open_tag = r"<\w[^<>]*>"
closed_tag = r"</[^<>]*>"

tag_pattern = open_tag + "|" + closed_tag
tag_tokenizer = RegexpTokenizer(tag_pattern)
text_tokenizer = RegexpTokenizer(tag_pattern, gaps=True)


@dataclass
class TextDescription:
    """Data class for article metadata."""

    pmid: int
    doi: str | None
    metadata: str


@dataclass
class ArticleMeta:
    title: str = ""
    authors: str = ""
    journal: str = ""
    volume: str = ""
    number: str | None = None
    pages: str = ""
    year: int = 0


@dataclass
class ParsedArticle:
    """Parsed content of a scientific article, source-format agnostic."""

    meta: ArticleMeta | None
    abstract: str | None
    body: str | None


@dataclass
class TextChunk:
    """Data class for chunks of text from research articles."""

    content: str
    pos: int


def concat(*strings: str | None, sep: str = "") -> str:
    """Concatenate a sequence of possibly null strings."""

    def is_not_none(s: str | None) -> TypeGuard[str]:
        return s is not None

    return sep.join(filter(is_not_none, strings))


def parse_file(file: str) -> _ElementTree:
    try:
        tree: _ElementTree = parse(file)
        return tree
    except XMLSyntaxError:
        print(f"{file} could not be parsed")
        raise


for _ns, _uri in {
    "ns": "https://dtd.nlm.nih.gov/ns/archiving/2.3/",
    "jats11": "https://jats.nlm.nih.gov/ns/archiving/1.1/",
    "jats12": "https://jats.nlm.nih.gov/ns/archiving/1.2/",
    "jats13": "https://jats.nlm.nih.gov/ns/archiving/1.3/",
    "jats": "https://jats.nlm.nih.gov/ns/archiving/1.4/",
    "ali": "http://www.niso.org/schemas/ali/1.0/",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "mml": "http://www.w3.org/1998/Math/MathML",
    "xlink": "http://www.w3.org/1999/xlink",
}.items():
    register_namespace(_ns, _uri)


def tree_as_string(tree: _ElementTree | _Element) -> str:
    return tostring(tree, method="c14n2").decode("utf-8")


def get_text(tree: _ElementTree) -> TextDescription:
    pmid = get_pmid(tree)
    doi = get_doi(tree)
    meta = get_metadata(tree)

    return TextDescription(pmid=pmid, doi=doi, metadata=meta)


def get_pmid(tree: _ElementTree) -> int:
    """Retrieve a Pubmed ID from `tree`.

    :param tree: ElementTree to be searched.
    :raises ValueError: Raise an exception when a Pubmed ID cannot be found.
    :return: Pubmed ID
    """
    pmid_path = "//*[name()='article-id'][@pub-id-type='pmid'][1]"
    pmid = tree.xpath(pmid_path)

    if isinstance(pmid, list) and isinstance(pmid[0], _Element):
        if pmid[0].text:
            return int(pmid[0].text)

    raise ValueError("Could not find a PMID.")


def get_doi(tree: _ElementTree) -> str | None:
    """Retrieve a DOI from `tree` if available.

    :param tree: ElementTree to be searched.
    :return: DOI, if available, otherwise None.
    """
    doi_path = "//*[name()='article-id'][@pub-id-type='doi'][1]"
    doi = tree.xpath(doi_path)

    if isinstance(doi, list) and isinstance(doi[0], _Element):
        if doi[0].text:
            return doi[0].text

    return None


def get_segments(tree: _ElementTree) -> list[_Element]:
    tree = transform_tree(tree)
    pathfinder: XPathEvaluator = XPathEvaluator(tree)
    abstract = "//*[@class='abstract']"

    non_metadata = "//*[@class = 'article-body']/"
    headers = "contains('h2h3h4h5h6', name())"
    pars = "name()='p' or name()='figure'"
    segtags = f"*[{headers} or {pars}]"
    body = non_metadata + segtags

    segments = pathfinder(abstract) + pathfinder(body)

    return segments


def get_metadata(tree: _ElementTree) -> str:
    pathfinder = XPathEvaluator(tree)
    metadata = pathfinder("//*[name()='journal-meta' or name()='article-meta']")
    return "\n".join(tostring(block, encoding="unicode").strip() for block in metadata)


def _front_text(elem: _Element, xpath: str) -> str:
    results = elem.xpath(xpath)
    return "".join(results).strip() if results else ""


def _parse_year(year_str: str) -> int:
    return int(year_str) if year_str.isdigit() else 0


def parse_jats_front(front: _Element) -> ArticleMeta:
    title = _front_text(front, ".//*[name()='article-title']//text()")

    surnames = front.xpath(
        ".//*[name()='contrib' and @contrib-type='author']//*[name()='surname']/text()"
    )
    given_names = front.xpath(
        ".//*[name()='contrib' and @contrib-type='author']"
        "//*[name()='given-names']/text()"
    )
    authors = "; ".join(
        f"{s}, {g}" if g else s
        for s, g in itertools.zip_longest(surnames, given_names, fillvalue="")
    )

    journal = _front_text(front, ".//*[name()='journal-title']/text()")
    volume = _front_text(front, ".//*[name()='volume']/text()")
    number = _front_text(front, ".//*[name()='issue']/text()") or None

    fpage = _front_text(front, ".//*[name()='fpage']/text()")
    lpage = _front_text(front, ".//*[name()='lpage']/text()")
    pages = f"{fpage}–{lpage}" if fpage and lpage else fpage

    year_str = _front_text(
        front,
        ".//*[name()='pub-date' and ("
        "@pub-type='ppub' or @pub-type='epub' or @date-type='pub'"
        ")]/*[name()='year']/text()",
    )
    if not year_str:
        year_str = _front_text(front, ".//*[name()='pub-date']/*[name()='year']/text()")
    year = _parse_year(year_str)

    return ArticleMeta(
        title=title,
        authors=authors,
        journal=journal,
        volume=volume,
        number=number,
        pages=pages,
        year=year,
    )


def parse_jats_article(record: _Element) -> ParsedArticle:
    # The XPaths must stay relative (".//"): a leading "//" is absolute over the
    # whole document, so parsing the articles of a multi-article <pmc-articleset>
    # in place would return the first article's content for every one of them.
    fronts = record.xpath(".//*[name()='front'][1]")
    abstract_els = record.xpath(".//*[name()='abstract'][1]")
    body_els = record.xpath(".//*[name()='body'][1]")

    return ParsedArticle(
        meta=parse_jats_front(fronts[0]) if fronts else None,
        abstract=tree_as_string(abstract_els[0]) if abstract_els else None,
        body=tree_as_string(body_els[0]) if body_els else None,
    )


def _pubmed_author_name(author: _Element) -> str:
    last = "".join(author.xpath("LastName/text()"))
    fore = "".join(author.xpath("ForeName/text()"))
    return f"{last}, {fore}" if fore else last


def parse_pubmed_article(record: _Element) -> ParsedArticle:
    title = _front_text(record, ".//ArticleTitle//text()")
    authors = "; ".join(
        _pubmed_author_name(a) for a in record.xpath(".//AuthorList/Author")
    )
    journal = _front_text(record, ".//Journal/Title/text()")
    pages = _front_text(record, ".//MedlinePgn/text()")

    ji = record.find(".//JournalIssue")
    volume = _front_text(ji, "Volume/text()") if ji is not None else ""
    number = _front_text(ji, "Issue/text()") or None if ji is not None else None
    year = _parse_year(_front_text(ji, "PubDate/Year/text()") if ji is not None else "")

    return ParsedArticle(
        meta=ArticleMeta(
            title=title,
            authors=authors,
            journal=journal,
            volume=volume,
            number=number,
            pages=pages,
            year=year,
        ),
        abstract=_front_text(record, ".//Abstract/AbstractText//text()") or None,
        body=None,
    )


def clean_namespaces(elem: _Element | _ElementTree) -> _Element | _ElementTree:
    for subelem in elem.getiterator():
        if not (
            isinstance(subelem, _Comment) or isinstance(subelem, _ProcessingInstruction)
        ):
            try:
                subelem.tag = QName(subelem).localname
            except ValueError as e:
                e.add_note(tostring(subelem).decode())
                raise

    cleanup_namespaces(elem)

    return elem


def segment_to_string(segment: _Element) -> str:
    segment = clean_namespaces(segment)

    return tostring(segment, method="xml", encoding="unicode")


def build_chunk(content: str, pos: int) -> dict[str, int | str]:
    prettified = tostring(
        clean_namespaces(fromstring(f"<chunk-body>{content}</chunk-body>")),
        pretty_print=True,
        encoding="unicode",
    )
    return {"content": prettified, "pos": pos}


def get_chunks(
    tree: _ElementTree, minlen: int = 4000, maxlen: int = 6000
) -> Iterator[TextChunk]:
    segments: Iterator[_Element] = iter(get_segments(tree))

    pos = itertools.count()
    yield build_chunk(content=segment_to_string(next(segments)), pos=next(pos))

    content = ""
    content_buffer = ""

    for seg in segments:
        segstring = segment_to_string(seg)

        if (
            seg.tag[-2:] in ("h1", "h2", "h3", "h4", "h5", "h6")
            and len(content) > minlen
        ):
            content_buffer = concat(content_buffer, segstring)
        elif not content_buffer and len(content) + len(segstring) <= maxlen:
            content = concat(content, segstring)
        else:
            content_buffer = concat(content_buffer, segstring)

        if len(content_buffer) >= minlen:
            yield build_chunk(content=content, pos=next(pos))
            content, content_buffer = content_buffer, ""

    content = concat(content, content_buffer)

    if content:
        yield build_chunk(content=content, pos=next(pos))


def transform_tree(
    tree: _ElementTree | _Element | str, style: str = "jats"
) -> _Element | _ElementTree:
    if isinstance(tree, str):
        tree = fromstring(tree)
    stylesheet = {"jats": "jats.xsl"}[style]
    path = XSLDIR / stylesheet
    xslt_transform = XSLT(parse(path))

    return xslt_transform(tree)


def transform_article(article_xml: str | bytes, style: str = "jats") -> str:
    if isinstance(article_xml, str):
        article_xml = article_xml.encode()

    article_xml = close_tags(article_xml)

    try:
        tree = fromstring(article_xml)
    except XMLSyntaxError as e:
        e.add_note(str(article_xml))
        raise
    else:
        return tostring(transform_tree(tree, style=style)).decode("utf-8")


def close_tags(xml: str | bytes) -> bytes:
    if isinstance(xml, bytes):
        closed = re.sub("<hr>", "<hr/>", xml.decode()).encode()
    else:
        closed = re.sub("<hr>", "<hr/>", xml).encode()

    return closed


class Tag(NamedTuple):
    tag: str
    start: int


def remove_tags(xml: str) -> str:
    return "".join(text_tokenizer.tokenize(xml))


def tokenize_xml(xml: str) -> str:
    return xml_char_tokenizer.tokenize(xml)


def reinsert_tags(text: str, xml: _Element | _ElementTree | str) -> str:
    if isinstance(xml, str):
        xml = fromstring(xml).getroottree()

    textit = chars(text)

    open_spans: list[_Element] = []
    original_elements = tuple(xml.iter())

    for event, elem in iterwalk(xml, events=("start", "end")):
        # check if elem wasn't added in a previous annotation step
        if elem in original_elements:
            elem = clean_namespaces(elem)
            root = True if elem == xml.getroot() else False
            if event == "start" and elem.text is not None:
                segment = "".join(itertools.islice(textit, len(elem.text)))
                elem, open_spans = annotate_text(elem, segment, open_spans, "text")
                if root:
                    xml._setroot(elem)
            elif event == "end" and elem.tail is not None:
                segment = "".join(itertools.islice(textit, len(elem.tail)))
                elem, open_spans = annotate_text(elem, segment, open_spans, "tail")

    xml = merge_children(promote_spans(xml))

    return tostring(xml, method="html", encoding="unicode")


def annotate_text(
    elem: _Element, text: str, open_spans: list[str], position: str
) -> tuple[_Element, list[_Element]]:
    new_spans: list[_Element] = []
    splits = re.findall(rf"{tag_pattern}|[^<>]+", text)

    context = elem

    # Reset `elem`'s text or tail. Those will be decided here.
    if position == "text":
        elem.text = ""
    else:
        elem.tail = ""

    for open_span in open_spans:
        subspan = deepcopy(open_span)
        if position == "text":
            context.insert(0, subspan)
        else:
            context.addnext(subspan)
        context = subspan
        position = "text"

    for split in splits:
        if split.startswith("<div"):
            # move prefix declarations from the div to the root
            div = Element("div", **attribs(split))

            root = elem
            while root.getparent() is not None:
                root = root.getparent()

            copy_curies(source=div, target=root)

        elif split.startswith("<span"):
            new = Element("span", **attribs(split))
            if position == "text":
                context.insert(0, new)
            else:
                context.addnext(new)
            context = new
            new_spans.append(deepcopy(new))
            position = "text"

        elif split == "</span>":
            position = "tail"
            if new_spans:
                new_spans.pop()
            else:
                open_spans.pop()

        elif split == "</div>":
            pass

        else:
            if position == "text":
                context.text = concat(context.text, split)
            else:
                context.tail = concat(context.tail, split)

    return elem, open_spans + new_spans


def copy_curies(source: Element, target: Element) -> None:
    if "prefix" in source.attrib:
        target.attrib["prefix"] = " ".join(curies(target) | curies(source))


def curies(elem: Element) -> set[str]:
    prefix = r"[a-zA-Z_][a-zA-Z_\-\.\d]*"

    # https://www.rfc-editor.org/rfc/rfc3986#appendix-B
    uri = (
        r"[^:/?#]+:"  # Scheme, ex. http:
        r"(?://[^/?# ]+)?"  # Authority (optional)
        r"[^?# ]*"  # Path
        r"(?:\?(?:[^# ]*))?"  # Query (optional)
        r"(?:#(?:\S*))?"  # Fragment (optional)
    )

    curie = re.compile(rf"({prefix}: ?{uri})")

    return set(re.findall(curie, elem.attrib.get("prefix", "")))


def promote_spans(tree: _ElementTree) -> _Element | _ElementTree:
    for node in tree.iter():
        if node.tag == "span":
            promote_span(node)

    return tree


def promote_span(span: _Element) -> None:
    parent = span.getparent()
    while (
        parent is not None and len(parent) == 1 and not parent.text and not parent.tail
    ):
        newspan = deepcopy(span)
        parent.remove(span)

        newspan.tail, parent.tail = parent.tail, None
        parent.text, newspan.text = newspan.text, None
        for child in newspan.getchildren():
            parent.append(child)

        try:
            parent.getparent().replace(parent, newspan)
        except AttributeError:
            pass
        finally:
            newspan.append(parent)


def merge_children(tree: _Element | _ElementTree) -> _Element | _ElementTree:
    for node in tree.iter():
        for cursor in range(len(node) - 1, 0, -1):
            current = node[cursor]
            preceding = node[cursor - 1]
            if (
                current.tag == preceding.tag
                and current.attrib == preceding.attrib
                and not preceding.tail
            ):
                node.replace(preceding, merge_nodes(preceding, current))
                node.remove(current)

    return tree


def merge_nodes(left: _Element, right: _Element) -> _Element:
    new = Element(left.tag, left.attrib)

    for child in left:
        new.append(child)
    new.text = left.text

    try:
        new[-1].tail = right.text
    except IndexError:
        new.text = concat(new.text, right.text)

    for child in right:
        new.append(child)

    new.tail = right.tail

    return new


def attribs(string: str) -> dict[str, str]:
    invalid_chars = r"\"'<>=\x00-\x1f\x7f-\x9f"
    attribute = rf"([^ {invalid_chars}]+)"
    value = rf"[\"\']([^{invalid_chars}]+)[\"\']"
    return dict(re.findall(rf"{attribute}={value}", string))


def chars(text: str) -> Iterator[str]:
    """Iterate over `text` returning every character plus any XML/HTML tag
    that immediately precedes it.

    If a character is followed by a </span>, return it along with the character
    as well.
    """

    tag_char = rf"({open_tag})|({closed_tag})|(.)"
    current: list[str] = []

    for split in re.findall(tag_char, text):
        last_aint_tag = current and re.match(tag_pattern, current[-1]) is None
        match split:
            case ("", s, ""):
                current.append(s)
                if last_aint_tag:
                    yield "".join(current)
                    current = []
            case (s, "", "") | ("", "", s):
                if last_aint_tag:
                    yield "".join(current)
                    current = []
                current.append(s)

    if current:
        yield "".join(current)


def split_metadata_body(xml: str) -> tuple[str, str]:
    xml_sans_chunk_tag = re.sub(r"</?chunk>", "", xml)
    splits = re.split(r"(</article-meta>)", xml_sans_chunk_tag)
    try:
        metadata = splits[0] + splits[1]
        body = splits[2]
        return metadata.strip(), body.strip()
    except IndexError:
        raise RuntimeError("Your XML does not have the expected format")


def replace_annotation(original: str, replacement: str) -> str:
    new_annotation = re.sub(
        r'<div class="chunk-body"[^>]*>(.*)</div>', r"\1", replacement
    )
    return re.sub(
        r"(<chunk-body[^>]*>)(.*)(</chunk-body.*)",
        rf"\1{new_annotation}\3",
        original,
    )
