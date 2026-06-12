import re
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def clean_inline_markdown(text):
    """
    Replaces basic markdown inline tags with ReportLab Paragraph XML-like tags.
    """
    # Replace bold **text** with <b>text</b>
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    # Replace italic *text* with <i>text</i>
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    # Replace backticks `code` with a monospace font
    text = re.sub(r"`(.*?)`", r'<font face="Courier"><b>\1</b></font>', text)
    return text

def parse_markdown_to_flowables(markdown_text, styles):
    """
    Parses a markdown string and returns a list of ReportLab Flowables.
    Supports headings, lists, tables, and standard paragraphs.
    """
    flowables = []
    lines = markdown_text.split("\n")
    
    in_list = False
    in_table = False
    table_rows = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # 1. Handle Table
        if line.startswith("|") and i + 1 < len(lines) and lines[i+1].strip().startswith("|") and "-" in lines[i+1]:
            in_table = True
            table_rows = []
            
            # Parse header row
            header_cols = [clean_inline_markdown(c.strip()) for c in line.split("|")[1:-1]]
            table_rows.append(header_cols)
            
            # Skip separator row (lines[i+1])
            i += 2
            
            # Read body rows
            while i < len(lines) and lines[i].strip().startswith("|"):
                body_cols = [clean_inline_markdown(c.strip()) for c in lines[i].split("|")[1:-1]]
                table_rows.append(body_cols)
                i += 1
                
            # Create ReportLab Table
            if len(table_rows) > 0:
                # Wrap cell text in Paragraph flowables so they autowrap!
                cell_flowables = []
                for r_idx, row in enumerate(table_rows):
                    row_flowables = []
                    for col in row:
                        style = styles['TableHeader'] if r_idx == 0 else styles['TableCell']
                        row_flowables.append(Paragraph(col, style))
                    cell_flowables.append(row_flowables)
                
                # Determine sensible column widths
                num_cols = len(table_rows[0])
                col_width = 460 / max(num_cols, 1) # total width / cols
                
                t = Table(cell_flowables, colWidths=[col_width]*num_cols)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4F46E5")), # Deep Indigo
                    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('BOTTOMPADDING', (0,0), (-1,0), 6),
                    ('TOPPADDING', (0,0), (-1,0), 6),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")), # Light gray grid
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F9FAFB"), colors.white]), # Alternating background
                    ('TOPPADDING', (0,1), (-1,-1), 5),
                    ('BOTTOMPADDING', (0,1), (-1,-1), 5),
                ]))
                flowables.append(t)
                flowables.append(Spacer(1, 10))
            
            in_table = False
            continue
            
        # If we reach here, we are not in a table.
        # 2. Handle Headings
        if line.startswith("# "):
            val = clean_inline_markdown(line[2:])
            flowables.append(Paragraph(val, styles['TitleStyle']))
            flowables.append(Spacer(1, 12))
        elif line.startswith("## "):
            val = clean_inline_markdown(line[3:])
            flowables.append(Paragraph(val, styles['Heading2Style']))
            flowables.append(Spacer(1, 8))
        elif line.startswith("### "):
            val = clean_inline_markdown(line[4:])
            flowables.append(Paragraph(val, styles['Heading3Style']))
            flowables.append(Spacer(1, 6))
            
        # 3. Handle Bullet points
        elif line.startswith("- ") or line.startswith("* "):
            val = clean_inline_markdown(line[2:])
            flowables.append(Paragraph(f"&bull; {val}", styles['BulletStyle']))
            # Small space after bullet items
            flowables.append(Spacer(1, 3))
            
        # 4. Handle numbered list
        elif re.match(r"^\d+\.\s+", line):
            prefix = re.match(r"^(\d+\.\s+)", line).group(1)
            val = clean_inline_markdown(line[len(prefix):])
            flowables.append(Paragraph(f"{prefix}{val}", styles['BulletStyle']))
            flowables.append(Spacer(1, 3))
            
        # 5. Handle empty lines
        elif not line:
            flowables.append(Spacer(1, 8))
            
        # 6. Handle standard paragraph
        else:
            val = clean_inline_markdown(line)
            flowables.append(Paragraph(val, styles['BodyStyle']))
            flowables.append(Spacer(1, 6))
            
        i += 1
        
    return flowables

def markdown_to_pdf(markdown_text, output_pdf_path, document_title="NotebookLM Export"):
    """
    Converts markdown text to a clean, professionally styled PDF file.
    """
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    
    # Establish document
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        rightMargin=54, # 0.75 in
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    # Base stylesheet
    base_styles = getSampleStyleSheet()
    
    # Create custom, premium styles
    styles = {}
    styles['TitleStyle'] = ParagraphStyle(
        'DocTitle',
        parent=base_styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#1E1B4B"), # Dark Navy Indigo
        spaceAfter=15
    )
    styles['Heading2Style'] = ParagraphStyle(
        'DocH2',
        parent=base_styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#4F46E5"), # Purple Indigo
        spaceBefore=12,
        spaceAfter=8
    )
    styles['Heading3Style'] = ParagraphStyle(
        'DocH3',
        parent=base_styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0D9488"), # Teal
        spaceBefore=8,
        spaceAfter=4
    )
    styles['BodyStyle'] = ParagraphStyle(
        'DocBody',
        parent=base_styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor("#374151") # Charcoal/Off-black
    )
    styles['BulletStyle'] = ParagraphStyle(
        'DocBullet',
        parent=base_styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#374151"),
        leftIndent=20
    )
    styles['TableHeader'] = ParagraphStyle(
        'TableHeader',
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=11,
        textColor=colors.white
    )
    styles['TableCell'] = ParagraphStyle(
        'TableCell',
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1F2937")
    )
    
    # Parse markdown into list of ReportLab Flowables
    story = []
    
    # Add a main title header
    story.append(Paragraph(document_title, styles['TitleStyle']))
    story.append(Spacer(1, 10))
    
    # Add a thin colored decorative line
    decor_table = Table([[""]], colWidths=[504], rowHeights=[2])
    decor_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#4F46E5")),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(decor_table)
    story.append(Spacer(1, 15))
    
    # Parse content
    flowables = parse_markdown_to_flowables(markdown_text, styles)
    story.extend(flowables)
    
    # Build the PDF document
    doc.build(story)
    return output_pdf_path
