from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib import colors
import re

def _is_log_message(line: str) -> bool:
    """Filter out system logs from PDF."""
    line = line.strip()
    if not line: return False
    
    # Symbols often used in logs
    if line.startswith(("■", "### ■", "**■")): return True
    
    log_prefixes = [
        "INFO:", "UserWarning:", "🌱", "📊", "🔍", "✅", "❌", "🐳", "🔌", "🔤", 
        "💾", "🔄", "⏱️", "📡", "🏛️", "🌿", "🕷️", "📺", "🚀", "⏰", "🤖", "💬", "🔮",
        "Warning:", "Error:", "Exception:", "Traceback", "Proceed with", 
        "Using cached", "Database contains", "Searching for", "Falling back",
        "Consulting ChatGPT", "Generating embedding", "Querying Qdrant",
        "Found collection", "Qdrant client", "Combined Data:", "Found in Qdrant",
        "AI Response", "AI recommendations", "AI expectations", "COMPLETE TWO-PHASE",
        "----------------------------------------", "=========="
    ]
    
    for prefix in log_prefixes:
        if line.startswith(prefix):
            return True
            
    # Remove lines that look like log headers
    if "STARTING COMPLETE PLANT GROWING ANALYSIS" in line: return True
    if "PHASE 1:" in line or "PHASE 2:" in line: return True
    
    return False

def _parse_markdown_tables(lines, start_idx):
    """Parse markdown tables from lines starting at start_idx."""
    table_lines = []
    i = start_idx
    
    while i < len(lines):
        line = lines[i].strip()
        # Check if it's a table row (starts and ends with |)
        if line.startswith('|') and line.endswith('|'):
            table_lines.append(line)
            i += 1
        else:
            break
    
    if not table_lines:
        return None, start_idx
    
    # Parse table - skip separator lines like |---|---|
    data = []
    for row in table_lines:
        cells = [c.strip() for c in row.split('|')[1:-1]]
        # Skip separator lines
        if cells and all(re.match(r'^[-:\s]+$', c) for c in cells):
            continue
        if cells:
            data.append(cells)
    
    if len(data) < 1:
        return None, start_idx
    
    return data, i

def generate_pdf_report(plant_name: str, content: str, session_id: str) -> str:
    """
    Generate a clean, formatted PDF report from the analysis content.
    """
    # Create results directory if it doesn't exist
    results_dir = Path("data/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Create filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{plant_name.replace(' ', '_')}_{timestamp}.pdf"
    filepath = results_dir / filename
    
    # Create PDF
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )
    
    # Container for the 'Flowable' objects
    story = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Title Style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.HexColor('#2D5016'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Heading 1 (e.g. # Header)
    h1_style = ParagraphStyle(
        'CustomH1',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a472a'),
        spaceBefore=20,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    
    # Heading 2 (e.g. ## Header)
    h2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2f855a'),
        spaceBefore=15,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )
    
    # Body Text
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        alignment=TA_LEFT,
        spaceAfter=6
    )
    
    # Bullet Point
    bullet_style = ParagraphStyle(
        'CustomBullet',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        leftIndent=20,
        bulletIndent=10,
        spaceAfter=4,
        bulletFontName='Helvetica'
    )
    
    # Add title page
    story.append(Paragraph(f"Growing Guide: {plant_name.title()}", title_style))
    story.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y')}", 
                          ParagraphStyle('Date', parent=styles['Normal'], alignment=TA_CENTER)))
    story.append(Spacer(1, 0.5*inch))
    
    # Process content line by line
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check for markdown table - convert to styled paragraphs instead
        if line.startswith('|') and '|' in line[1:]:
            table_data, next_idx = _parse_markdown_tables(lines, i)
            if table_data and len(table_data) >= 1:
                # Check if first row is header
                has_header = len(table_data[0]) <= 3 and all(len(c) < 20 for c in table_data[0])
                data_rows = table_data[1:] if has_header else table_data
                
                # Convert to styled paragraphs
                for row in data_rows:
                    if len(row) >= 2:
                        label = row[0].strip()
                        value = ' '.join(row[1:]).strip()
                        if label and value:
                            story.append(Paragraph(f"<b>{label}:</b> {value}", body_style))
                            story.append(Spacer(1, 4))
                i = next_idx
                continue
        
        # Skip empty lines or logs
        if not line or _is_log_message(line):
            i += 1
            continue
            
        # Clean up markdown artifacts
        clean_line = line.replace('**', '').replace('*', '')
        
        # Determine style based on markdown syntax
        if line.startswith('# '):
            story.append(Paragraph(clean_line.replace('# ', ''), h1_style))
        elif line.startswith('## '):
            story.append(Paragraph(clean_line.replace('## ', ''), h2_style))
        elif line.startswith('### '):
            story.append(Paragraph(clean_line.replace('### ', ''), h2_style))
        elif line.startswith('- ') or line.startswith('* '):
            # Bullet point
            text = clean_line.replace('- ', '').replace('* ', '')
            story.append(Paragraph(f"• {text}", bullet_style))
        elif line.startswith('1. '):
            # Numbered list
            story.append(Paragraph(clean_line, bullet_style))
        else:
            # Standard paragraph
            story.append(Paragraph(clean_line, body_style))
        
        i += 1
            
    # Build PDF
    try:
        doc.build(story)
        return str(filepath)
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return ""