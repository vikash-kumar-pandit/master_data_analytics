import io
import logging
import polars as pl
from fpdf import FPDF
from pptx import Presentation
from pptx.util import Inches, Pt

logger = logging.getLogger(__name__)


def _pdf_output_bytes(pdf: FPDF) -> bytes:
    output = pdf.output()
    if isinstance(output, bytes):
        return output
    if isinstance(output, bytearray):
        return bytes(output)
    if isinstance(output, str):
        return output.encode("latin-1", errors="ignore")
    return bytes(output)


class PDFTable(FPDF):
    def header(self):
        try:
            self.set_font("Helvetica", "B", 16)
            title = getattr(self, "report_title", "Data Analysis Report")
            safe_title = str(title)[:100]  # Limit title length
            self.cell(0, 10, safe_title, border=False, align="C")
            self.ln(10)
        except Exception as e:
            logger.error(f"Error in PDF header: {e}")


def generate_pdf_in_memory(dataframe: pl.DataFrame, analysis_summary: dict) -> bytes:
    """Generate PDF with error handling."""
    try:
        if dataframe is None:
            dataframe = pl.DataFrame()
        if analysis_summary is None:
            analysis_summary = {}
        
        pdf = PDFTable()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Data Analysis Report", border=False, align="C")
        pdf.ln(12)

        pdf.set_font("Helvetica", size=11)
        rows_count = analysis_summary.get('rows', 0)
        category = str(analysis_summary.get('category', 'Unknown'))[:50]
        cols_count = analysis_summary.get('cols', 0)
        
        pdf.cell(0, 8, f"Total Rows Processed: {rows_count}")
        pdf.ln(6)
        pdf.cell(0, 8, f"Data Category Detected: {category}")
        pdf.ln(6)
        pdf.cell(0, 8, f"Columns Detected: {cols_count}")
        pdf.ln(10)
        
        sample_dataframe = dataframe.head(20)

        if sample_dataframe.columns and sample_dataframe.height > 0:
            try:
                column_count = len(sample_dataframe.columns)
                if column_count > 0:
                    col_width = max(5, pdf.epw / column_count)

                    pdf.set_font("Helvetica", "B", 9)
                    for column_name in sample_dataframe.columns:
                        safe_col = str(column_name)[:50]
                        pdf.cell(col_width, 8, safe_col, border=1, align="C")
                    pdf.ln(8)

                    pdf.set_font("Helvetica", size=9)
                    for values in sample_dataframe.iter_rows():
                        for value in values:
                            safe_value = str(value)[:100]
                            pdf.cell(col_width, 7, safe_value, border=1)
                        pdf.ln(7)
            except Exception as e:
                logger.error(f"Error adding table to PDF: {e}")
                pdf.set_font("Helvetica", size=10)
                pdf.cell(0, 10, f"Error rendering table: {str(e)[:100]}")
        else:
            pdf.set_font("Helvetica", size=10)
            pdf.cell(0, 10, "No tabular columns were available to render.")

        try:
            return _pdf_output_bytes(pdf)
        except Exception as e:
            logger.error(f"Error outputting PDF: {e}")
            return b"%PDF-1.4\n%EOF"
    
    except Exception as e:
        logger.exception(f"Failed to generate PDF: {e}")
        return b"%PDF-1.4\n%EOF"


def generate_structured_report_pdf(*, title: str, subtitle: str, sections: list[dict]) -> bytes:
    """Generate structured PDF report with error handling."""
    try:
        if not isinstance(title, str):
            title = str(title or "Report")
        if not isinstance(subtitle, str):
            subtitle = str(subtitle or "")
        if sections is None:
            sections = []
        if not isinstance(sections, list):
            sections = []
        
        validated_sections = []
        for section in sections:
            if isinstance(section, dict):
                validated_sections.append(section)
        
        pdf = PDFTable()
        pdf.report_title = title
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        try:
            pdf.set_font("Helvetica", "B", 16)
            safe_title = str(title)[:100]
            pdf.cell(0, 10, safe_title, border=False, align="C")
            pdf.ln(8)
            
            if subtitle:
                pdf.set_font("Helvetica", "", 11)
                safe_subtitle = str(subtitle)[:100]
                pdf.cell(0, 7, safe_subtitle, border=False, align="C")
                pdf.ln(10)
            else:
                pdf.ln(4)
        except Exception as e:
            logger.error(f"Error adding title to PDF: {e}")

        for section in validated_sections:
            try:
                pdf.set_font("Helvetica", "B", 12)
                heading = str(section.get("heading") or "Section")[:100]
                pdf.cell(0, 9, heading)
                pdf.ln(7)
                
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
                                pdf.cell(0, 7, f"[Error rendering row: {str(e)[:50]}]")
                pdf.ln(3)
            except Exception as e:
                logger.error(f"Error adding section to PDF: {e}")
                pdf.set_font("Helvetica", size=10)
                pdf.cell(0, 10, f"[Error rendering section: {str(e)[:100]}]")

        try:
            return _pdf_output_bytes(pdf)
        except Exception as e:
            logger.error(f"Error outputting PDF: {e}")
            return b"%PDF-1.4\n%EOF"
    
    except Exception as e:
        logger.exception(f"Failed to generate structured PDF: {e}")
        return b"%PDF-1.4\n%EOF"


def generate_structured_report_pptx(*, title: str, subtitle: str, sections: list[dict]) -> bytes:
    """Generate PPTX report with template styling."""
    try:
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
            title_slide_layout = presentation.slide_layouts[6]  # blank layout
            title_slide = presentation.slides.add_slide(title_slide_layout)
            
            from pptx.util import Inches, Pt, Emu
            from pptx.dml.color import RGBColor
            from pptx.enum.text import PP_ALIGN
            
            bg = title_slide.background
            fill = bg.fill
            fill.solid()
            fill.fore_color.rgb = RGBColor(0x1A, 0x23, 0x7E)
            
            title_box = title_slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(12.333), Inches(1.5))
            tf = title_box.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = str(title)[:100]
            p.font.size = Pt(40)
            p.font.bold = True
            p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            p.alignment = PP_ALIGN.CENTER
            
            if subtitle:
                sub_box = title_slide.shapes.add_textbox(Inches(0.5), Inches(4.2), Inches(12.333), Inches(1))
                tf2 = sub_box.text_frame
                tf2.word_wrap = True
                p2 = tf2.paragraphs[0]
                p2.text = str(subtitle)[:100]
                p2.font.size = Pt(20)
                p2.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
                p2.alignment = PP_ALIGN.CENTER
            
            date_box = title_slide.shapes.add_textbox(Inches(0.5), Inches(6.8), Inches(12.333), Inches(0.4))
            tf3 = date_box.text_frame
            p3 = tf3.paragraphs[0]
            from datetime import datetime
            p3.text = f"Generated on {datetime.now().strftime('%B %d, %Y')}"
            p3.font.size = Pt(12)
            p3.font.color.rgb = RGBColor(0xAA, 0xAA, 0xAA)
            p3.alignment = PP_ALIGN.CENTER
        except Exception as e:
            logger.error(f"Error creating title slide: {e}")

        for section in sections:
            try:
                if not isinstance(section, dict):
                    continue
                    
                slide_layout = presentation.slide_layouts[6]
                slide = presentation.slides.add_slide(slide_layout)
                
                bg = slide.background
                fill = bg.fill
                fill.solid()
                fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                
                header = slide.shapes.add_textbox(Inches(0.4), Inches(0.3), Inches(12.5), Inches(0.8))
                htf = header.text_frame
                hp = htf.paragraphs[0]
                hp.text = str(section.get("heading") or "Section")[:100]
                hp.font.size = Pt(28)
                hp.font.bold = True
                hp.font.color.rgb = RGBColor(0x1A, 0x23, 0x7E)
                
                line = slide.shapes.add_shape(1, Inches(0.4), Inches(1.05), Inches(12.5), Inches(0.05))
                line.fill.solid()
                line.fill.fore_color.rgb = RGBColor(0x1A, 0x23, 0x7E)
                line.line.fill.background()
                
                body = slide.shapes.add_textbox(Inches(0.5), Inches(1.3), Inches(12.333), Inches(5.8))
                tf = body.text_frame
                tf.word_wrap = True
                rows = section.get("rows") or []
                
                if not rows:
                    p = tf.paragraphs[0]
                    p.text = "No data available"
                    p.font.size = Pt(16)
                    p.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
                    continue

                first_row = True
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                        
                    try:
                        label = str(row.get("label") or "")[:80]
                        value = str(row.get("value") or "")[:200]
                        p = tf.paragraphs[0] if first_row else tf.add_paragraph()
                        p.text = f"{label}: {value}" if label else str(value)[:200]
                        p.font.size = Pt(16)
                        p.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
                        p.space_after = Pt(8)
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
            fallback = Presentation()
            fallback_out = io.BytesIO()
            fallback.save(fallback_out)
            return fallback_out.getvalue()
    
    except Exception as e:
        logger.exception(f"Failed to generate PPTX: {e}")
        fallback = Presentation()
        fallback_out = io.BytesIO()
        fallback.save(fallback_out)
        return fallback_out.getvalue()
