<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:jats="https://jats.nlm.nih.gov/ns/archiving/1.3/" xmlns:xlink="http://www.w3.org/1999/xlink" version="2.0" exclude-result-prefixes="jats xlink">
  <xsl:output method="html" encoding="UTF-8" indent="yes"/>

  <!-- PMC ID and version for S3 image URL construction -->
  <xsl:variable name="pmcid" select="//*[local-name()='article-id'][@pub-id-type='pmcid']"/>
  <xsl:variable name="pmcversion" select="'1'"/>

  <!-- Suppress front matter — used only for variable extraction above -->
  <xsl:template match="*[local-name()='front']"/>

  <!-- Template for the root element (body) -->
  <xsl:template match="/jats:body">
    <div class="jats-body">
      <xsl:apply-templates/>
    </div>
  </xsl:template>

  <!-- sec → section -->
  <xsl:template match="*[local-name()='sec']">
    <section>
      <xsl:for-each select="@*">
        <xsl:attribute name="{local-name()}">
          <xsl:value-of select="."/>
        </xsl:attribute>
      </xsl:for-each>
      <xsl:apply-templates/>
    </section>
  </xsl:template>

  <!-- title inside sec → depth-based heading (h2–h6); prepend sibling label if present -->
  <xsl:template match="*[local-name()='sec']/*[local-name()='title']">
    <xsl:variable name="depth" select="count(ancestor::*[local-name()='sec'])"/>
    <xsl:variable name="level">
      <xsl:choose>
        <xsl:when test="$depth &gt;= 5">h6</xsl:when>
        <xsl:when test="$depth = 4">h5</xsl:when>
        <xsl:when test="$depth = 3">h4</xsl:when>
        <xsl:when test="$depth = 2">h3</xsl:when>
        <xsl:otherwise>h2</xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:element name="{$level}">
      <xsl:if test="preceding-sibling::*[local-name()='label']">
        <xsl:value-of select="preceding-sibling::*[local-name()='label']"/>
        <xsl:text> </xsl:text>
      </xsl:if>
      <xsl:apply-templates/>
    </xsl:element>
  </xsl:template>

  <!-- label inside sec is rendered via the title template above; suppress standalone -->
  <xsl:template match="*[local-name()='sec']/*[local-name()='label']"/>

  <!-- abstract → section.abstract; drop redundant <title> direct child -->
  <xsl:template match="*[local-name()='abstract']">
    <section class="abstract">
      <xsl:apply-templates/>
    </section>
  </xsl:template>

  <!-- abstract title (e.g. "Abstract") is redundant in context; suppress -->
  <xsl:template match="*[local-name()='abstract']/*[local-name()='title']"/>

  <!-- fig → figure: graphic/media first, then label + caption below -->
  <xsl:template match="*[local-name()='fig']">
    <figure>
      <xsl:for-each select="@*">
        <xsl:attribute name="{local-name()}">
          <xsl:value-of select="."/>
        </xsl:attribute>
      </xsl:for-each>
      <xsl:apply-templates select="*[local-name()='label']"/>
      <xsl:apply-templates select="*[local-name()='graphic' or local-name()='media']"/>
      <xsl:apply-templates select="*[local-name()='caption']"/>
      <xsl:apply-templates select="*[local-name()!='graphic' and local-name()!='media' and local-name()!='label' and local-name()!='caption']"/>
    </figure>
  </xsl:template>

  <!-- table-wrap → figure -->
  <xsl:template match="*[local-name()='table-wrap']">
    <figure>
      <xsl:for-each select="@*">
        <xsl:attribute name="{local-name()}">
          <xsl:value-of select="."/>
        </xsl:attribute>
      </xsl:for-each>
      <xsl:apply-templates/>
    </figure>
  </xsl:template>

  <!-- supplementary-material → figure -->
  <xsl:template match="*[local-name()='supplementary-material']">
    <figure class="supplementary-material">
      <xsl:for-each select="@*[local-name() != 'content-type']">
        <xsl:attribute name="{local-name()}">
          <xsl:value-of select="."/>
        </xsl:attribute>
      </xsl:for-each>
      <xsl:apply-templates/>
    </figure>
  </xsl:template>

  <!-- graphic → img with PMC URL -->
  <xsl:template match="*[local-name()='graphic']">
    <xsl:variable name="href" select="@*[local-name()='href']"/>
    <img>
      <xsl:attribute name="src">
        <xsl:text>https://pmc-oa-opendata.s3.amazonaws.com/</xsl:text>
        <xsl:value-of select="$pmcid"/>
        <xsl:text>.</xsl:text>
        <xsl:value-of select="$pmcversion"/>
        <xsl:text>/</xsl:text>
        <xsl:value-of select="$href"/>
        <xsl:if test="not(contains($href, '.'))"><xsl:text>.jpg</xsl:text></xsl:if>
      </xsl:attribute>
      <xsl:attribute name="alt">
        <xsl:value-of select="ancestor::*[local-name()='fig']/*[local-name()='label']"/>
      </xsl:attribute>
    </img>
  </xsl:template>

  <!-- media → a with PMC URL -->
  <xsl:template match="*[local-name()='media']">
    <xsl:variable name="href" select="@*[local-name()='href']"/>
    <a>
      <xsl:attribute name="href">
        <xsl:text>https://pmc-oa-opendata.s3.amazonaws.com/</xsl:text>
        <xsl:value-of select="$pmcid"/>
        <xsl:text>.</xsl:text>
        <xsl:value-of select="$pmcversion"/>
        <xsl:text>/</xsl:text>
        <xsl:value-of select="$href"/>
        <xsl:if test="not(contains($href, '.'))"><xsl:text>.jpg</xsl:text></xsl:if>
      </xsl:attribute>
      <xsl:apply-templates/>
    </a>
  </xsl:template>

  <!-- caption → figcaption -->
  <xsl:template match="*[local-name()='caption']">
    <figcaption>
      <xsl:apply-templates/>
    </figcaption>
  </xsl:template>

  <!-- label inside figure-like containers → span.label -->
  <xsl:template match="*[local-name()='fig']/*[local-name()='label']
                      | *[local-name()='table-wrap']/*[local-name()='label']
                      | *[local-name()='supplementary-material']/*[local-name()='label']">
    <span class="label"><xsl:apply-templates/></span>
  </xsl:template>

  <!-- xref → a -->
  <xsl:template match="*[local-name()='xref']">
    <a>
      <xsl:if test="@rid">
        <xsl:attribute name="href">#<xsl:value-of select="@rid"/></xsl:attribute>
      </xsl:if>
      <xsl:apply-templates/>
    </a>
  </xsl:template>

  <!-- ext-link → a -->
  <xsl:template match="*[local-name()='ext-link']">
    <a>
      <xsl:if test="@*[local-name()='href']">
        <xsl:attribute name="href">
          <xsl:value-of select="@*[local-name()='href']"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:apply-templates/>
    </a>
  </xsl:template>

  <!-- italic → em -->
  <xsl:template match="*[local-name()='italic']">
    <em><xsl:apply-templates/></em>
  </xsl:template>

  <!-- bold → strong -->
  <xsl:template match="*[local-name()='bold']">
    <strong><xsl:apply-templates/></strong>
  </xsl:template>

  <!-- sc → span.sc (small caps via CSS) -->
  <xsl:template match="*[local-name()='sc']">
    <span class="sc"><xsl:apply-templates/></span>
  </xsl:template>

  <!-- Generic template to remove namespace but keep tag names and attributes -->
  <xsl:template match="*">
    <xsl:element name="{local-name()}">
      <xsl:for-each select="@*">
        <xsl:attribute name="{local-name()}">
          <xsl:value-of select="."/>
        </xsl:attribute>
      </xsl:for-each>
      <xsl:apply-templates/>
    </xsl:element>
  </xsl:template>
</xsl:stylesheet>
