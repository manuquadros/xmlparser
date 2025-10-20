"""Module providing tools for the manipulation of XML articles."""

import importlib
import itertools
import os
import pathlib
import re
from collections.abc import Iterator, Sequence
from copy import deepcopy
from dataclasses import dataclass
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

XSLDIR = importlib.resources.files("xmlparser.stylesheets")

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


def tree_as_string(tree: _ElementTree | _Element) -> str:
    namespaces = {
        "ns": "https://dtd.nlm.nih.gov/ns/archiving/2.3/",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "mml": "http://www.w3.org/1998/Math/MathML",
        "xlink": "http://www.w3.org/1999/xlink",
    }

    for key, value in namespaces.items():
        register_namespace(key, value)

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
    pars = "name()='p' or name()='table-wrap' or name()='fig'"
    segtags = f"*[{headers} or {pars}]"
    body = non_metadata + segtags

    segments = pathfinder(abstract) + pathfinder(body)

    return segments


def get_metadata(tree: _ElementTree) -> str:
    pathfinder = XPathEvaluator(tree)
    metadata = pathfinder("//*[name()='journal-meta' or name()='article-meta']")
    return "\n".join(
        tostring(block, encoding="unicode").strip() for block in metadata
    )


def clean_namespaces(elem: _Element | _ElementTree) -> _Element | _ElementTree:
    for subelem in elem.getiterator():
        if not (
            isinstance(subelem, _Comment)
            or isinstance(subelem, _ProcessingInstruction)
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
    finally:
        return tostring(transform_tree(tree, style=style))


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
                elem, open_spans = annotate_text(
                    elem, segment, open_spans, "text"
                )
                if root:
                    xml._setroot(elem)
            elif event == "end" and elem.tail is not None:
                segment = "".join(itertools.islice(textit, len(elem.tail)))
                elem, open_spans = annotate_text(
                    elem, segment, open_spans, "tail"
                )

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
        parent is not None
        and len(parent) == 1
        and not parent.text
        and not parent.tail
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
