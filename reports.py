"""
Report generation module for FIMS
Handles PDF and Excel report generation
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from datetime import datetime
import os

class ReportGenerator:
    def __init__(self, output_dir='reports'):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def generate_bill_pdf(self, bill_data):
        """Generate PDF bill"""
        filename = f"bill_{bill_data[0]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph("<b>PAYAL FERTILIZERS</b>", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Bill header
        bill_header = Paragraph(f"<b>BILL #{bill_data[0]}</b>", styles['Heading2'])
        elements.append(bill_header)
        elements.append(Spacer(1, 0.1*inch))
        
        # Bill details
        details_data = [
            ['Bill Type:', bill_data[1].upper()],
            ['Generated On:', bill_data[6]],
            ['Dispatch ID:', bill_data[2] if bill_data[2] else 'N/A'],
            ['Rate:', f'₹{bill_data[3]:.2f}'],
            ['Quantity:', f'{bill_data[4]:.2f} MT'],
            ['', ''],
            ['Total Amount:', f'₹{bill_data[5]:.2f}'],
        ]
        
        details_table = Table(details_data, colWidths=[2*inch, 3*inch])
        details_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 12),
            ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold', 14),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.red),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('GRID', (0, -2), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(details_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Footer
        footer = Paragraph("<i>Thank you for your business!</i>", styles['Normal'])
        elements.append(footer)
        
        doc.build(elements)
        return filepath
