import io
import logging
import polars as pl
from fpdf import FPDF
from pptx import Presentation
from pptx.util import Inches, Pt

logger = logging.getLogger(__name__)


class PDFTable(FPDF):
    def header(self):
        try:
            self.set_font("Helvetica", "B", 16)
            title = getattr(self, "report_title", "Data Analysis Report")
            safe_title = str(title)[:100]  # Limit title length
            self.cell(0, 10, safe_title, border=False, ln=True, align="C")
            self.ln(10)
        except Exception as e:
            logger.error(f"Error in PDF header: {e}")


def generate_pdf_in_memory(dataframe: pl.DataFrame, analysis_summary: dict) -> bytes:
    """Generate PDF with error handling."""
    try:
        # Validate inputs
        if dataframe is None:
            dataframe = pl.DataFrame()
        if analysis_summary is None:
            analysis_summary = {}
        
        pdf = PDFTable()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        try:
            pdf.set_font("Helvetica", size=12)
            rows_count = analysis_summary.get('rows', 0)
            category = str(analysis_summary.get('category', 'Unknown'))[:50]
            cols_count = analysis_summary.get('cols', 0)
            
            pdf.cell(0, 10, f"Total Rows Processed: {rows_count}", ln=True)
            pdf.cell(0, 10, f"Data Category Detected: {category}", ln=True)
            pdf.cell(0, 10, f"Columns Detected: {cols_count}", ln=True)
            pdf.ln(8)
        except Exception as e:
            logger.error(f"Error adding summary to PDF: {e}")
            pdf.cell(0, 10, f"Error rendering summary: {str(e)[:100]}", ln=True)

        sample_dataframe = dataframe.head(20)

        if sample_dataframe.columns and sample_dataframe.height > 0:
            try:
                column_count = len(sample_dataframe.columns)
                if column_count > 0:
                    col_width = max(5, pdf.epw / column_count)

                    pdf.set_font("Helvetica", "B", 10)
                    for column_name in sample_dataframe.columns:
                        safe_col = str(column_name)[:50]
                        pdf.cell(col_width, 8, safe_col, border=1)
                    pdf.ln(8)

                    pdf.set_font("Helvetica", size=9)
                    for values in sample_dataframe.iter_rows():
                        for value in values:
                            safe_value = str(value)[:100]
                            pdf.cell(col_width, 8, safe_value, border=1)
                        pdf.ln(8)
            except Exception as e:
                logger.error(f"Error adding table to PDF: {e}")
                pdf.set_font("Helvetica", size=10)
                pdf.cell(0, 10, f"Error rendering table: {str(e)[:100]}", ln=True)
        else:
            pdf.set_font("Helvetica", size=10)
            pdf.cell(0, 10, "No tabular columns were available to render.", ln=True)

        try:
            pdf_output = pdf.output(dest="S")
            if isinstance(pdf_output, (bytes, bytearray)):
                return bytes(pdf_output)
            return pdf_output.encode("latin-1")
        except Exception as e:
            logger.error(f"Error outputting PDF: {e}")
            # Return minimal valid PDF
            return b"%PDF-1.4\n%EOF"
    
    except Exception as e:
        logger.exception(f"Failed to generate PDF: {e}")
        return b"%PDF-1.4\n%EOF"


def generate_structured_report_pdf(*, title: str, subtitle: str, sections: list[dict]) -> bytes:
    """Generate structured PDF report with error handling."""
    try:
        # Validate inputs
        if not isinstance(title, str):
            title = str(title or "Report")
        if not isinstance(subtitle, str):
            subtitle = str(subtitle or "")
        if sections is None:
            sections = []
        if not isinstance(sections, list):
            sections = []
        
        # Validate section structure
        validated_sections = []
        for section in sections:
            if isinstance(section, dict):
                validated_sections.append(section)
        
        pdf = PDFTable()
        pdf.report_title = title
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        try:
            pdf.set_font("Helvetica", size=12)
            safe_title = str(title)[:100]
            safe_subtitle = str(subtitle)[:100]
            pdf.cell(0, 10, safe_title, ln=True)
            pdf.cell(0, 10, safe_subtitle, ln=True)
            pdf.ln(4)
        except Exception as e:
            logger.error(f"Error adding title to PDF: {e}")

        for section in validated_sections:
            try:
                pdf.set_font("Helvetica", "B", 12)
                heading = str(section.get("heading") or "Section")[:100]
                pdf.cell(0, 9, heading, ln=True)
                
                pdf.set_font("Helvetica", size=10)
                rows = section.get("rows") or []
                
                if isinstance(rows, list):
                    for row in rows:
                        if isinstance(row, dict):
                            label = str(row.get("label") or "")[:100]
                            value = str(row.get("value") or "")[:200]
                            try:
                                pdf.multi_cell(0, 7, f"{label}: {value}")
                            except Exception as e:
                                logger.warning(f"Error adding row to PDF: {e}")
                                pdf.cell(0, 7, f"[Error rendering row: {str(e)[:50]}]", ln=True)
                pdf.ln(2)
            except Exception as e:
                logger.error(f"Error adding section to PDF: {e}")
                pdf.set_font("Helvetica", size=10)
                pdf.cell(0, 10, f"[Error rendering section: {str(e)[:100]}]", ln=True)

        try:
            pdf_output = pdf.output(dest="S")
            if isinstance(pdf_output, (bytes, bytearray)):
                return bytes(pdf_output)
            return pdf_output.encode("latin-1")
        except Exception as e:
            logger.error(f"Error outputting PDF: {e}")
            return b"%PDF-1.4\n%EOF"
    
    except Exception as e:
        logger.exception(f"Failed to generate structured PDF: {e}")
        return b"%PDF-1.4\n%EOF"


def generate_structured_report_pptx(*, title: str, subtitle: str, sections: list[dict]) -> bytes:
    """Generate PPTX report with error handling."""
    try:
        # Validate inputs
        if not isinstance(title, str):
            title = str(title or "Report")
        if not isinstance(subtitle, str):
            subtitle = str(subtitle or "")
        if sections is None:
            sections = []
        if not isinstance(sections, list):
            sections = []
        
        presentation = Presentation()
        presentation.slide_width = Inches(13.333)
        presentation.slide_height = Inches(7.5)

        try:
            title_slide_layout = presentation.slide_layouts[0]
            title_slide = presentation.slides.add_slide(title_slide_layout)
            title_slide.shapes.title.text = str(title)[:100]
            title_slide.placeholders[1].text = str(subtitle)[:100]
        except Exception as e:
            logger.error(f"Error creating title slide: {e}")

        for section in sections:
            try:
                if not isinstance(section, dict):
                    continue
                    
                slide_layout = presentation.slide_layouts[1]
                slide = presentation.slides.add_slide(slide_layout)
                slide.shapes.title.text = str(section.get("heading") or "Section")[:100]

                body = slide.shapes.placeholders[1].text_frame
                body.clear()
                rows = section.get("rows") or []
                
                if not rows:
                    paragraph = body.paragraphs[0]
                    paragraph.text = "No data available"
                    paragraph.font.size = Pt(18)
                    continue

                first_row = True
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                        
                    try:
                        label = str(row.get("label") or "")[:100]
                        value = str(row.get("value") or "")[:200]
                        paragraph = body.paragraphs[0] if first_row else body.add_paragraph()
                        paragraph.text = f"{label}: {value}"
                        paragraph.level = 0
                        paragraph.font.size = Pt(18)
                        first_row = False
                    except Exception as e:
                        logger.warning(f"Error adding row to PPTX: {e}")
                        
            except Exception as e:
                logger.error(f"Error adding section to PPTX: {e}")

        try:
            output = io.BytesIO()
            presentation.save(output)
            return output.getvalue()
        except Exception as e:
            logger.error(f"Error outputting PPTX: {e}")
            # Return empty PPTX as fallback
            fallback = Presentation()
            fallback_out = io.BytesIO()
            fallback.save(fallback_out)
            return fallback_out.getvalue()
    
    except Exception as e:
        logger.exception(f"Failed to generate PPTX: {e}")
        # Return empty PPTX
        fallback = Presentation()
        fallback_out = io.BytesIO()
        fallback.save(fallback_out)
        return fallback_out.getvalue()
