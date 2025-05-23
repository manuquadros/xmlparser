<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:jats="https://jats.nlm.nih.gov/ns/archiving/1.3/"
    exclude-result-prefixes="jats">

    <!-- Output HTML -->
    <xsl:output method="html" encoding="UTF-8" indent="yes"/>

    <!-- Template for the root element (body) -->
    <xsl:template match="/jats:body">
        <div class="jats-body">
            <xsl:apply-templates/>
        </div>
    </xsl:template>

    <!-- Template for sections (jats:sec) -->
    <xsl:template match="jats:sec">
        <div class="section">
            <xsl:apply-templates/>
        </div>
    </xsl:template>

    <!-- Template for titles (jats:title) -->
    <xsl:template match="jats:title">
        <h2><xsl:value-of select="."/></h2>
    </xsl:template>

    <!-- Template for tables (jats:table) -->
    <xsl:template match="jats:table">
        <table><xsl:value-of select="."/></table>
    </xsl:template>

    <!-- Template for table data cells (jats:td) -->
    <xsl:template match="jats:td">
        <td><xsl:value-of select="."/></td>
    </xsl:template>

    <!-- Template for table header cells (jats:th) -->
    <xsl:template match="jats:th">
        <th><xsl:value-of select="."/></th>
    </xsl:template>

    <!-- Template for table data cells (jats:td) -->
    <xsl:template match="jats:td">
        <td><xsl:value-of select="."/></td>
    </xsl:template>

    <!-- Template for paragraphs (jats:p) -->
    <xsl:template match="jats:p">
        <p><xsl:apply-templates/></p>
    </xsl:template>

    <!-- Template for italic (jats:italic) -->
    <xsl:template match="jats:italic">
        <em><xsl:value-of select="."/></em>
    </xsl:template>

    <!-- Template for cross-references (jats:xref) -->
    <xsl:template match="jats:xref">
        <a href="#{@rid}">"><xsl:value-of select="."/></a>
    </xsl:template>

    <!-- Default template to copy other elements as is -->
    <xsl:template match="*">
        <xsl:copy>
            <xsl:apply-templates/>
        </xsl:copy>
    </xsl:template>

</xsl:stylesheet>
