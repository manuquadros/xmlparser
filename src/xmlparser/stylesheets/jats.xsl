<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:jats="https://jats.nlm.nih.gov/ns/archiving/1.3/" version="2.0" exclude-result-prefixes="jats">
  <!-- Output HTML -->
  <xsl:output method="html" encoding="UTF-8" indent="yes"/>
  <!-- Template for the root element (body) -->
  <xsl:template match="/jats:body">
    <div class="jats-body">
      <xsl:apply-templates/>
    </div>
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
