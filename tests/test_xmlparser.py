from copy import deepcopy

from lxml.etree import Element
from xmlparser.xmlparser import (
    chars,
    clean_namespaces,
    copy_curies,
    curies,
    fromstring,
    merge_children,
    promote_spans,
    reinsert_tags,
    remove_tags,
    replace_annotation,
    tostring,
    transform_article,
)

tryptophan = (
    "<div>with the indole precursor <sc>l</sc>-tryptophan, we observed</div>"
)
italic = "<div>with the <italic>indole precursor l-tryptophan</italic>, we observed</div>"
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
        attrib={
            "prefix": "schema: http://schema.org/ dc: http://purl.org/dc/terms/"
        },
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

    assert tostring(empty, method="c14n2") == tostring(
        another_empty, method="c14n2"
    )

    copy_curies(source=empty, target=first)
    assert tostring(empty, method="c14n2") == tostring(
        another_empty, method="c14n2"
    )

    assert curies(first) == curies(target2)

    copy_curies(source=empty, target=another_empty)

    assert tostring(empty, method="c14n2") == tostring(
        another_empty, method="c14n2"
    )


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
    assert (
        reinsert_tags(annotated_tryptophan, tryptophan) == expected_tryptophan
    )

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
    original = [
        '<p>The bacteria were grown on the GYS medium in a 2-liter scale fermentor in batch mode operation under pH and temperature controlled conditions. Under this conditions the cell yield was doubled (9.5 mg/ml vs. 4.8 mg/ml dry cell weight) and the cultivation time was reduced to one third (60 vs. 180 hours) as compared with shaken flasks. These results are in good agreement with the literature [<xref ref-type="bibr" rid="B12">12</xref>]. We found that addition of 2 g/l cholesterol to the culture broth [<xref ref-type="bibr" rid="B12">12</xref>], prepared as an aqueous emulsion with the aid of Tween 80 at a weight ratio 2:1 results in a high yield of COX production [<xref ref-type="bibr" rid="B9">9</xref>], but the preparation procedure of that emulsion had a marked influence in the final enzyme yield, although not on the cell weight, as seen in Table <xref ref-type="table" rid="T1">1</xref>. The spray-dry method resulted advantageous because the cholesterol :Tween 80 emulsion formed readily and COX production increased in overall by three times with respect to the preparation of the cholesterol:Tween 80 mixture at the flame. Enzyme production improvement resulted larger as cell-linked (3.8-fold) than as extracellular (2.3-fold). This overall increase of COX production can be due to a better availability of cholesterol to the cell since particle size obtained by spray-dry is smaller.</p>',
        '<chunk-body><p xmlns="https://jats.nlm.nih.gov/ns/archiving/1.3/" xmlns:ali="http://www.niso.org/schemas/ali/1.0/" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">Distribution of COX activity among detergent depleted and detergent rich phases after induction of phase separation of cell extracts done with the indicated concentration of Triton X-114. (a) Total activity; (b) Specific activity.</p><p xmlns="https://jats.nlm.nih.gov/ns/archiving/1.3/" xmlns:ali="http://www.niso.org/schemas/ali/1.0/" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">As Triton X-114 concentration is increased, COX partitions towards the detergent rich phase, increasing its specific activity (Figures <xref ref-type="fig" rid="F2">2b</xref> and <xref ref-type="fig" rid="F3">3b</xref>) thus resulting in enzyme purification and also in enzyme concentration since the volume of the detergent-rich phase is much lower than the initial volume. The 1% concentration of detergent was an exception to this rule since COX partitioned toward the depleted phase under our working conditions. Partitioning of commercial COX in buffers containing 1% Triton X-114 occurred toward the rich phase and was very influenced by the buffer concentration [<xref ref-type="bibr" rid="B16">16</xref>]. Therefore, it seems that the composition of phase separation media is extremely important to the partitioning of particular proteins.</p><p xmlns="https://jats.nlm.nih.gov/ns/archiving/1.3/" xmlns:ali="http://www.niso.org/schemas/ali/1.0/" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">The purification was made evident by running samples of COX from cells and culture broth in SDS-PAGE gels. Figure <xref ref-type="fig" rid="F4">4</xref> shows that in both cases the detergent-rich phase was enriched in some proteins, including COX, whereas the depleted phase showed other different protein bands.</p><fig xmlns="https://jats.nlm.nih.gov/ns/archiving/1.3/" xmlns:ali="http://www.niso.org/schemas/ali/1.0/" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" position="float" id="F4">\n          <label>Figure 4</label>\n          <caption>\n            <p>SDS-PAGE of COX fractions using 3% Triton X-114 for extraction, purification and concentration, (a) Cell extracts: lane 1, Mw markers; lane 2, commercial COX; lane 3, total extracted proteins; lane 4, proteins in detergent depleted phase; lane 5, proteins in detergent rich phase, (b) Culture broth: lane 1, Mw markers; lane 2, commercial COX; lane 3, proteins in detergent rich phase; lane 4, total proteins in culture broth; lane 5, proteins in detergent depleted phase. Arrows indicated the COX band.</p>\n          </caption>\n          <graphic xlink:href="1472-6750-2-3-4"/>\n        </fig><p xmlns="https://jats.nlm.nih.gov/ns/archiving/1.3/" xmlns:ali="http://www.niso.org/schemas/ali/1.0/" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">SDS-PAGE of COX fractions using 3% Triton X-114 for extraction, purification and concentration, (a) Cell extracts: lane 1, Mw markers; lane 2, commercial COX; lane 3, total extracted proteins; lane 4, proteins in detergent depleted phase; lane 5, proteins in detergent rich phase, (b) Culture broth: lane 1, Mw markers; lane 2, commercial COX; lane 3, proteins in detergent rich phase; lane 4, total proteins in culture broth; lane 5, proteins in detergent depleted phase. Arrows indicated the COX band.</p><p xmlns="https://jats.nlm.nih.gov/ns/archiving/1.3/" xmlns:ali="http://www.niso.org/schemas/ali/1.0/" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">An exceptional result was obtained when performing COX purification from the culture broth supplemented with a 6% w/v Triton X-114. The total activity recovered after phase separation was ca. 3.5-fold that measured in the broth before phase separation. This result suggests that soluble COX produced by the culture is not fully active and that it can be activated by a treatment with 6% Triton X-114 but not with 4% or less. Further increase of Triton X-114 concentration results in no improvement with respect to 6% (results not shown). This phenomenon was not observed with COX extracted from cells, therefore the enzyme most likely exists in a fully active form in the cells.</p></chunk-body>',
    ]

    serialized = [
        '<div prefix="d3o: https://purl.dsmz.de/schema/">The <span resource="#T1" typeof="d3o:OOS">bacteria</span> were grown on the GYS medium in a 2-liter scale fermentor in batch mode operation under pH and temperature controlled conditions. Under this conditions the cell yield was doubled (9.5 mg/ml vs. 4.8 mg/ml dry cell weight) and the cultivation time was reduced to one third (60 vs. 180 hours) as compared with shaken flasks. These results are in good agreement with the literature [12]. We found that addition of 2 g/l cholesterol to the culture broth [12], prepared as an aqueous emulsion with the aid of Tween 80 at a weight ratio 2:1 results in a high yield of COX production [9], but the preparation procedure of that emulsion had a marked influence in the final enzyme yield, although not on the cell weight, as seen in Table 1. The spray-dry method resulted advantageous because the cholesterol :Tween <span resource="#T2" typeof="d3o:Strain">80</span> emulsion formed readily and COX production increased in overall by three times with respect to the preparation of the cholesterol:Tween <span resource="#T3" typeof="d3o:Strain">80</span> mixture at the flame. Enzyme production improvement resulted larger as cell-linked (3.8-fold) than as extracellular (2.3-fold). This overall increase of COX production can be due to a better availability of cholesterol to the cell since particle size obtained by spray-dry is smaller.</div>',
        '<div prefix="d3o: https://purl.dsmz.de/schema/">Distribution of COX activity among detergent depleted and detergent rich phases after induction of phase separation of cell extracts done with the indicated concentration of Triton X-114. (a) Total activity; (b) Specific activity.As Triton X-114 concentration is increased, COX partitions towards the detergent rich phase, increasing its specific activity (Figures 2b and 3b) thus resulting in enzyme purification and also in enzyme concentration since the volume of the detergent-rich phase is much lower than the initial volume. The 1% concentration of detergent was an exception to this rule since COX partitioned toward the depleted phase under our working conditions. Partitioning of commercial COX in buffers containing 1% Triton X-114 occurred toward the rich phase and was very influenced by the buffer concentration [16]. Therefore, it seems that the composition of phase separation media is extremely important to the partitioning of particular proteins.The purification was made evident by running samples of COX from cells and culture broth in SDS-PAGE gels. Figure 4 shows that in both cases the detergent-rich phase was enriched in some proteins, including COX, whereas the depleted phase showed other different protein bands.           Figure 4                        SDS-PAGE of COX fractions using 3% Triton X-114 for extraction, purification and concentration, (a) Cell extracts: lane 1, Mw markers; lane 2, commercial COX; lane 3, total extracted proteins; lane 4, proteins in detergent depleted phase; lane 5, proteins in detergent rich phase, (b) Culture broth: lane 1, Mw markers; lane 2, commercial COX; lane 3, proteins in detergent rich phase; lane 4, total proteins in culture broth; lane 5, proteins in detergent depleted phase. Arrows indicated the COX band.                               SDS-PAGE of COX fractions using 3% Triton X-114 for extraction, purification and concentration, (a) Cell extracts: lane 1, Mw markers; lane 2, commercial COX; lane 3, total extracted proteins; lane 4, proteins in detergent depleted phase; lane 5, proteins in detergent rich phase, (b) Culture broth: lane 1, Mw markers; lane 2, commercial COX; lane 3, proteins in detergent rich phase; lane 4, total proteins in culture broth; lane 5, proteins in detergent depleted phase. Arrows indicated the COX band.An exceptional result was obtained when performing COX purification from the culture broth supplemented with a 6% w/v Triton X-114. The total activity recovered after phase separationseparation was ca. 3.5-fold that measured in the broth before phase separation. This result suggests that soluble COX produced by the culture is not fully active and that it can be activated by a treatment with 6% Triton X-114 but not with 4% or less. Further increase of Triton X-114 concentration results in no improvement with respect to 6% (results not shown). This phenomenon was not observed with COX extracted from cells, therefore the enzyme most likely exists in a fully active form in the cells.</div>',
    ]

    goal = [
        '<p prefix="d3o: https://purl.dsmz.de/schema/">The <span resource="#T1" typeof="d3o:OOS">bacteria</span> were grown on the GYS medium in a 2-liter scale fermentor in batch mode operation under pH and temperature controlled conditions. Under this conditions the cell yield was doubled (9.5 mg/ml vs. 4.8 mg/ml dry cell weight) and the cultivation time was reduced to one third (60 vs. 180 hours) as compared with shaken flasks. These results are in good agreement with the literature [<xref ref-type="bibr" rid="B12">12</xref>]. We found that addition of 2 g/l cholesterol to the culture broth [<xref ref-type="bibr" rid="B12">12</xref>], prepared as an aqueous emulsion with the aid of Tween 80 at a weight ratio 2:1 results in a high yield of COX production [<xref ref-type="bibr" rid="B9">9</xref>], but the preparation procedure of that emulsion had a marked influence in the final enzyme yield, although not on the cell weight, as seen in Table <xref ref-type="table" rid="T1">1</xref>. The spray-dry method resulted advantageous because the cholesterol :Tween <span resource="#T2" typeof="d3o:Strain">80</span> emulsion formed readily and COX production increased in overall by three times with respect to the preparation of the cholesterol:Tween <span resource="#T3" typeof="d3o:Strain">80</span> mixture at the flame. Enzyme production improvement resulted larger as cell-linked (3.8-fold) than as extracellular (2.3-fold). This overall increase of COX production can be due to a better availability of cholesterol to the cell since particle size obtained by spray-dry is smaller.</p>',
        '<chunk-body prefix="d3o: https://purl.dsmz.de/schema/"><p>Distribution of COX activity among detergent depleted and detergent rich phases after induction of phase separation of cell extracts done with the indicated concentration of Triton X-114. (a) Total activity; (b) Specific activity.As Triton X-114 concentration is increased, COX partitions towards the detergent rich phase, increasing its specific activity (Figures <xref ref-type="fig" rid="F2">2b</xref> and <xref ref-type="fig" rid="F3">3b</xref>) thus resulting in enzyme purification and also in enzyme concentration since the volume of the detergent-rich phase is much lower than the initial volume. The 1% concentration of detergent was an exception to this rule since COX partitioned toward the depleted phase under our working conditions. Partitioning of commercial COX in buffers containing 1% Triton X-114 occurred toward the rich phase and was very influenced by the buffer concentration [<xref ref-type="bibr" rid="B16">16</xref>The purification was made evident by running samples of COX from cells and culture broth in SDS-PAGE gels. Figure <xref ref-type="fig" rid="F4">4</xref> shows that in both cases the detergent-rich phase was enriched in some proteins, including COX, whereas the depleted phase showed other different protein bands.</p><fig xmlns:xlink="http://www.w3.org/1999/xlink" position="float" id="F4">           <label>Figure 4</label>           <caption>             <p>SDS-PAGE of COX fractions using 3% Triton X-114 for extraction, purification and concentration, (a) Cell extracts: lane 1, Mw markers; lane 2, commercial COX; lane 3, total extracted proteins; lane 4, proteins in detergent depleted phase; lane 5, proteins in detergent rich phase, (b) Culture broth: lane 1, Mw markers; lane 2, commercial COX; lane 3, proteins in detergent rich phase; lane 4, total proteins in culture broth; lane 5, proteins in detergent depleted phase. Arrows indicated the COX band.</p>           </caption>           <graphic xlink:href="1472-6750-2-3-4"></graphic>         </fig><p>SDS-PAGE of COX fractions using 3% Triton X-114 for extraction, purification and concentration, (a) Cell extracts: lane 1, Mw markers; lane 2, commercial COX; lane 3, total extracted proteins; lane 4, proteins in detergent depleted phase; lane 5, proteins in detergent rich phase, (b) Culture broth: lane 1, Mw markers; lane 2, commercial COX; lane 3, proteins in detergent rich phase; lane 4, total proteins in culture broth; lane 5, proteins in detergent depleted phase. Arrows indicated the COX band.An exceptional result was obtained when performing COX purification from the culture broth supplemented with a 6% w/v Triton X-114. The total activity recovered after phase separationseparation was ca. 3.5-fold that measured in the broth before phase separation. This result suggests that soluble COX produced by the culture is not fully active and that it can be activated by a treatment with 6% Triton X-114 but not with 4% or less. Further increase of Triton X-114 concentration results in no improvement with respect to 6% (results not shown). This phenomenon was not observed with COX extracted from cells, therefore the enzyme most likely exists in a fully active form in </p></chunk-body>',
    ]

    for s, o, g in zip(serialized, original, goal):
        assert reinsert_tags(s, o) == g


def test_div_with_attribs():
    div = (
        '<div prefix="d3o: https://purl.dsmz.de/schema/"> '
        "Crystallization and preliminary X-ray diffraction analysis of two N-terminal "
        "fragments of the DNA-cleavage domain of topoisomerase IV from <span"
        ' resource="#T1" typeof="d3o:Bacteria">Staphylococcus aureus</span>'
    )
    assert (
        next(chars(div)) == '<div prefix="d3o: https://purl.dsmz.de/schema/"> '
    )


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
    og = """<annotation><journal-meta xmlns="https://dtd.nlm.nih.gov/ns/archiving/2.3/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xlink="http://www.w3.org/1999/xlink">
      <journal-id journal-id-type="nlm-ta">BMC Biotechnol</journal-id>
      <journal-title>BMC Biotechnology</journal-title>
      <issn pub-type="epub">1472-6750</issn>
      <publisher>
        <publisher-name>BioMed Central</publisher-name>
        <publisher-loc>London</publisher-loc>
      </publisher>
    </journal-meta>
<article-meta xmlns="https://dtd.nlm.nih.gov/ns/archiving/2.3/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xlink="http://www.w3.org/1999/xlink">
    </article-meta><chunk-body prefix="d3o: https://purl.dsmz.de/schema/"><p>Results from a typical batch fermentation are shown in Figure <xref ref-type="fig" rid="F1">1</xref>. Three stages can be differentiated during the fermentation process, (i) A first stage (0–16 h), in which 02 consumption increases continuously and HCl is consumed to keep the pH constant to 6.75. Buckland et al. [<xref ref-type="bibr" rid="B12">12</xref>] found that pH of the culture rose by 0.5 units in the first part of growth, and then fell. An exponential increase of cell mass is observed and low levels of COX activity appear linked to cells, (ii) The second stage (16–45 h) is characterized by a strong 02 consumption and a consumption of base. In this phase aerobic metabolism drives the cell growth but the growth rate is certainly limited by the O<sub>2</sub> availability – note pO<sub>2</sub> is nearly zero under continuous stirring and air supply-. This stage is also characterized by a high rate of COX production of both types, cell-linked and extracellular, (iii) The third stage (45 h to the end of the process) a second phase of consumption of acid was recorded whereas pO<sub>2</sub> increased again to reach saturating levels. The greatest increase of cell-linked COX production was observed in this stage whilst extracellular COX production stopped.</p>         <fig xmlns:xlink="http://www.w3.org/1999/xlink" position="float" id="F1">           <label>Figure 1</label>           <caption>             <p>Characterization of the <italic><span class="entity" resource="#T1" typeof="d3o:Bacteria">R. erythropolis</span></italic> fermentation process: biomass and production of cell-linked and extracellular COX. Enzyme activities are given as units/ml of cell culture. The data shown are from a single experiment but are representative of three separate replicates.</p>           </caption>           <graphic xlink:href="1472-6750-2-3-1"></graphic>         </fig>         <p>The profile of fermentation was very similar to that obtained by Buckland et al. [<xref ref-type="bibr" rid="B12">12</xref>] but differed in the accumulation of extracellular COX: the strain of <span class="entity" resource="#T2" typeof="OOS">Nocardia</span> (<span class="entity" resource="#T3" typeof="d3o:Strain">NCIB 10554</span>) used by these authors produced very low levels of extracellular enzyme while the strain tested in this work produces high levels. They also tested the effect of dissolved oxygen tension on the production of COX and found that in limiting conditions of oxygen supply the production of cell-linked COX was low. As seen in Figure <xref ref-type="fig" rid="F1">1</xref>, when oxygen supply is limiting (in the second stage) the rate of cell-linked COX production decreases, however is in these conditions when extracellular COX production takes place. Thus, there seem to be some relation between dissolved oxygen tension and extracellular COX production by the strain used in this work.</p>         <p>The results obtained are coherent with those presented in a previous study in shaken flasks [<xref ref-type="bibr" rid="B9">9</xref>], where extracellular COX production is large and arises from the partial solubilization of the cell-linked enzyme [<xref ref-type="bibr" rid="B20">20</xref>,<xref ref-type="bibr" rid="B21">21</xref>]. After 70 hours of fermentation the total enzyme activity obtained was ca. 360 U/ml, being 230 U/ml cell-linked and 130 U/ml extracellular, thus the cell-linked to extracellular ratio is 1.26. This ratio in shaken flasks ranged from 1.26, using the same amount of Tween 80 as in this work (0.1%), to 1.38, using 1% Tween 80, but in the latter the overall yields of COX production were 7-fold smaller [<xref ref-type="bibr" rid="B9">9</xref>]. The overall yield obtained in this work is comparable to that obtained by Buckland et al. [<xref ref-type="bibr" rid="B12">12</xref>] and by Minut et al. [<xref ref-type="bibr" rid="B17">17</xref>] but larger than that of Cheetham et al. [<xref ref-type="bibr" rid="B22">22</xref>]. Watanabe et al [<xref ref-type="bibr" rid="B24">24</xref>] compared the cell-linked and extracellular COX production of 31 strains of the genus <italic><span class="entity" resource="#T4" typeof="OOS">Rhodococcus</span></italic> and <italic><span class="entity" resource="#T2" typeof="OOS">Nocardia</span></italic> and found that among the best extracellular COX producers, the strains <span class="entity" resource="#T6" typeof="d3o:Bacteria"><italic>Rhodococcus</italic> sp</span>. N° <span class="entity" resource="#T7" typeof="d3o:Strain">31</span> and <italic><span class="entity" resource="#T8" typeof="d3o:Bacteria">R. equi</span></italic> N° <span class="entity" resource="#T9" typeof="d3o:Strain">24</span>, displayed the highest cell-linked to extracellular ratio, 1.32 and 2.68 respectively.</p></chunk-body></annotation>"""

    annotation = """<div class="chunk-body" prefix="d3o: https://purl.dsmz.de/schema/"><p>In a previous work [<xref ref-type="bibr" rid="B9">9</xref>] we described the cell-bound and extracellular <span class="entity" resource="#T1" typeof="d3o:Enzyme" id="1"><button class="entity" type="button" typeof="d3o:Enzyme" resource="#T1">cholesterol oxidase</button></span> activities from <italic><span class="entity" resource="#T2" typeof="d3o:Bacteria" id="2"><button class="entity" type="button" typeof="d3o:Bacteria" resource="#T2">R. erythropolis</button></span></italic> <span class="entity" resource="#T3" typeof="d3o:Strain" id="3"><button class="entity" type="button" typeof="d3o:Strain" resource="#T3">ATCC</button></span> <span class="entity" resource="#T4" typeof="d3o:Strain" id="4"><button class="entity" type="button" typeof="d3o:Strain" resource="#T4">25544</button></span>, achieving in optimal conditions 55% cell-bound and 45% extracellular activity. Their enzymatic properties strongly supported the idea that the particulate and the extracellular cholesterol oxidases are two different forms of the same enzyme with an estimated molecular mass of 55 kDa. In this work we optimize the culture conditions in a 2-liter fermentor of this extracellular <span class="entity" resource="#T1" typeof="d3o:Enzyme" id="5"><button class="entity" type="button" typeof="d3o:Enzyme" resource="#T1">cholesterol oxidase</button></span> producer strain and carry out the extraction, partial purification and concentration of both types of <span class="entity" resource="#T1" typeof="d3o:Enzyme" id="6"><button class="entity" type="button" typeof="d3o:Enzyme" resource="#T1">cholesterol oxidase</button></span> by using Triton X-114 phase separation. The results obtained are very promising for the use of this strain and this technique in the industrial processing of <span class="entity" resource="#T7" typeof="OOS" id="7">bacteria</span> to obtain <span class="entity" resource="#T1" typeof="d3o:Enzyme" id="8"><button class="entity" type="button" typeof="d3o:Enzyme" resource="#T1">cholesterol oxidase</button></span>.</p>                 <h3>Results and discussion</h3>                <h4>Batch cultivation of <span class="entity" resource="#T2" typeof="d3o:Bacteria" id="9"><button class="entity" type="button" typeof="d3o:Bacteria" resource="#T2">R. erythropolis</button></span> (<span class="entity" resource="#T10" typeof="d3o:Strain" id="10"><button class="entity" type="button" typeof="d3o:Strain" resource="#T10">ATCC 25544</button></span>)</h4>         <p>The <span class="entity" resource="#T7" typeof="OOS" id="11">bacteria</span> were grown on the GYS medium in a 2-liter scale fermentor in batch mode operation under pH and temperature controlled conditions. Under this conditions the cell yield was doubled (9.5 mg/ml vs. 4.8 mg/ml dry cell weight) and the cultivation time was reduced to one third (60 vs. 180 hours) as compared with shaken flasks. These results are in good agreement with the literature [<xref ref-type="bibr" rid="B12">12</xref>]. We found that addition of 2 g/l cholesterol to the culture broth [<xref ref-type="bibr" rid="B12">12</xref>], prepared as an aqueous <span class="entity" resource="#T12" typeof="d3o:Enzyme" id="12"><button class="entity" type="button" typeof="d3o:Enzyme" resource="#T12">emulsion</button></span> with the aid of Tween 80 at a weight ratio 2:1 results in a high yield of <span class="entity" typeof="d3o:Enzyme" resource="#T5" id="15">COX</span> production [<xref ref-type="bibr" rid="B9">9</xref>], but the preparation procedure of that <span class="entity" resource="#T12" typeof="d3o:Enzyme" id="13"><button class="entity" type="button" typeof="d3o:Enzyme" resource="#T12">emulsion</button></span> had a marked influence in the final enzyme yield, although not on the cell weight, as seen in Table <xref ref-type="table" rid="T1">1</xref>. The spray-dry method resulted advantageous because the cholesterol :Tween 80 <span class="entity" resource="#T12" typeof="d3o:Enzyme" id="14"><button class="entity" type="button" typeof="d3o:Enzyme" resource="#T12">emulsion</button></span> formed readily and COX production increased in overall by three times with respect to the preparation of the cholesterol:Tween 80 mixture at the flame. Enzyme production improvement resulted larger as cell-linked (3.8-fold) than as extracellular (2.3-fold). This overall increase of COX production can be due to a better availability of cholesterol to the cell since particle size obtained by spray-dry is smaller.</p>         <table-wrap position="float" id="T1">           <label>Table 1</label>                        <p>Effect of the cholesterol emuIsification method on the production of COX.</p>                      <table frame="hsides" rules="groups">             <thead>               <tr>                 <td>                 </td><td align="center" colspan="2">                   <bold>COX activity (U/ml)<sup>*</sup></bold>                 </td>                 <td>               </td></tr>             </thead>             <tbody>               <tr>                 <td align="center">                   <bold>Emulsification cholesterol method</bold>                 </td>                 <td align="center">                   <bold>Cell-linked</bold>                 </td>                 <td align="center">                   <bold>extracellular</bold>                 </td>                 <td align="center">                   <bold>Dry weight (mg/ml)</bold>                 </td>               </tr>               <tr>                 <td colspan="4">                   <hr>                 </td>               </tr>               <tr>                 <td align="center">Spray-dry</td>                 <td align="center">230</td>                 <td align="center">140</td>                 <td align="center">8.75</td>               </tr>               <tr>                 <td align="center">At the flame</td>                 <td align="center">60</td>                 <td align="center">60</td>                 <td align="center">9.05</td>               </tr>               <tr>                 <td align="center">Improvement</td>                 <td align="center">3.8</td>                 <td align="center">2.3</td>                 <td align="center">0.97</td>               </tr>             </tbody>           </table>           <table-wrap-foot>             <p><sup>*</sup>Enzymatic activity figures correspond to 70 hours of fermentation.</p></table-wrap-foot></table-wrap></div>"""

    assert (
        replace_annotation(og, annotation)
        == f"""<annotation><journal-meta xmlns="https://dtd.nlm.nih.gov/ns/archiving/2.3/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xlink="http://www.w3.org/1999/xlink">
      <journal-id journal-id-type="nlm-ta">BMC Biotechnol</journal-id>
      <journal-title>BMC Biotechnology</journal-title>
      <issn pub-type="epub">1472-6750</issn>
      <publisher>
        <publisher-name>BioMed Central</publisher-name>
        <publisher-loc>London</publisher-loc>
      </publisher>
    </journal-meta>
<article-meta xmlns="https://dtd.nlm.nih.gov/ns/archiving/2.3/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xlink="http://www.w3.org/1999/xlink">
    </article-meta><chunk-body prefix="d3o: https://purl.dsmz.de/schema/"><p>In a previous work [<xref ref-type="bibr" rid="B9">9</xref>] we described the cell-bound and extracellular <span class="entity" resource="#T1" typeof="d3o:Enzyme" id="1"><button class="entity" type="button" typeof="d3o:Enzyme" resource="#T1">cholesterol oxidase</button></span> activities from <italic><span class="entity" resource="#T2" typeof="d3o:Bacteria" id="2"><button class="entity" type="button" typeof="d3o:Bacteria" resource="#T2">R. erythropolis</button></span></italic> <span class="entity" resource="#T3" typeof="d3o:Strain" id="3"><button class="entity" type="button" typeof="d3o:Strain" resource="#T3">ATCC</button></span> <span class="entity" resource="#T4" typeof="d3o:Strain" id="4"><button class="entity" type="button" typeof="d3o:Strain" resource="#T4">25544</button></span>, achieving in optimal conditions 55% cell-bound and 45% extracellular activity. Their enzymatic properties strongly supported the idea that the particulate and the extracellular cholesterol oxidases are two different forms of the same enzyme with an estimated molecular mass of 55 kDa. In this work we optimize the culture conditions in a 2-liter fermentor of this extracellular <span class="entity" resource="#T1" typeof="d3o:Enzyme" id="5"><button class="entity" type="button" typeof="d3o:Enzyme" resource="#T1">cholesterol oxidase</button></span> producer strain and carry out the extraction, partial purification and concentration of both types of <span class="entity" resource="#T1" typeof="d3o:Enzyme" id="6"><button class="entity" type="button" typeof="d3o:Enzyme" resource="#T1">cholesterol oxidase</button></span> by using Triton X-114 phase separation. The results obtained are very promising for the use of this strain and this technique in the industrial processing of <span class="entity" resource="#T7" typeof="OOS" id="7">bacteria</span> to obtain <span class="entity" resource="#T1" typeof="d3o:Enzyme" id="8"><button class="entity" type="button" typeof="d3o:Enzyme" resource="#T1">cholesterol oxidase</button></span>.</p>                 <h3>Results and discussion</h3>                <h4>Batch cultivation of <span class="entity" resource="#T2" typeof="d3o:Bacteria" id="9"><button class="entity" type="button" typeof="d3o:Bacteria" resource="#T2">R. erythropolis</button></span> (<span class="entity" resource="#T10" typeof="d3o:Strain" id="10"><button class="entity" type="button" typeof="d3o:Strain" resource="#T10">ATCC 25544</button></span>)</h4>         <p>The <span class="entity" resource="#T7" typeof="OOS" id="11">bacteria</span> were grown on the GYS medium in a 2-liter scale fermentor in batch mode operation under pH and temperature controlled conditions. Under this conditions the cell yield was doubled (9.5 mg/ml vs. 4.8 mg/ml dry cell weight) and the cultivation time was reduced to one third (60 vs. 180 hours) as compared with shaken flasks. These results are in good agreement with the literature [<xref ref-type="bibr" rid="B12">12</xref>]. We found that addition of 2 g/l cholesterol to the culture broth [<xref ref-type="bibr" rid="B12">12</xref>], prepared as an aqueous <span class="entity" resource="#T12" typeof="d3o:Enzyme" id="12"><button class="entity" type="button" typeof="d3o:Enzyme" resource="#T12">emulsion</button></span> with the aid of Tween 80 at a weight ratio 2:1 results in a high yield of <span class="entity" typeof="d3o:Enzyme" resource="#T5" id="15">COX</span> production [<xref ref-type="bibr" rid="B9">9</xref>], but the preparation procedure of that <span class="entity" resource="#T12" typeof="d3o:Enzyme" id="13"><button class="entity" type="button" typeof="d3o:Enzyme" resource="#T12">emulsion</button></span> had a marked influence in the final enzyme yield, although not on the cell weight, as seen in Table <xref ref-type="table" rid="T1">1</xref>. The spray-dry method resulted advantageous because the cholesterol :Tween 80 <span class="entity" resource="#T12" typeof="d3o:Enzyme" id="14"><button class="entity" type="button" typeof="d3o:Enzyme" resource="#T12">emulsion</button></span> formed readily and COX production increased in overall by three times with respect to the preparation of the cholesterol:Tween 80 mixture at the flame. Enzyme production improvement resulted larger as cell-linked (3.8-fold) than as extracellular (2.3-fold). This overall increase of COX production can be due to a better availability of cholesterol to the cell since particle size obtained by spray-dry is smaller.</p>         <table-wrap position="float" id="T1">           <label>Table 1</label>                        <p>Effect of the cholesterol emuIsification method on the production of COX.</p>                      <table frame="hsides" rules="groups">             <thead>               <tr>                 <td>                 </td><td align="center" colspan="2">                   <bold>COX activity (U/ml)<sup>*</sup></bold>                 </td>                 <td>               </td></tr>             </thead>             <tbody>               <tr>                 <td align="center">                   <bold>Emulsification cholesterol method</bold>                 </td>                 <td align="center">                   <bold>Cell-linked</bold>                 </td>                 <td align="center">                   <bold>extracellular</bold>                 </td>                 <td align="center">                   <bold>Dry weight (mg/ml)</bold>                 </td>               </tr>               <tr>                 <td colspan="4">                   <hr>                 </td>               </tr>               <tr>                 <td align="center">Spray-dry</td>                 <td align="center">230</td>                 <td align="center">140</td>                 <td align="center">8.75</td>               </tr>               <tr>                 <td align="center">At the flame</td>                 <td align="center">60</td>                 <td align="center">60</td>                 <td align="center">9.05</td>               </tr>               <tr>                 <td align="center">Improvement</td>                 <td align="center">3.8</td>                 <td align="center">2.3</td>                 <td align="center">0.97</td>               </tr>             </tbody>           </table>           <table-wrap-foot>             <p><sup>*</sup>Enzymatic activity figures correspond to 70 hours of fermentation.</p></table-wrap-foot></table-wrap></chunk-body></annotation>"""
    )
