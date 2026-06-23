import polars as pl
from fpdf import FPDF
import logging

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


class PDFReport(FPDF):
    def header(self):
        try:
            self.set_font("Helvetica", "B", 16)
            self.cell(0, 10, "Automated Big Data Analysis Report", align="C")
            self.ln(5)
        except Exception as e:
            logger.error(f"Error in PDF header: {e}")


def create_pdf_in_memory(ai_summary: str, dataframe: pl.DataFrame) -> bytes:
    """Generate PDF with comprehensive error handling."""
    try:
        # Validate inputs
        if not isinstance(ai_summary, str):
            ai_summary = str(ai_summary or "")
        if not ai_summary or ai_summary.strip() == "":
            ai_summary = "No AI summary available."
        
        if dataframe is None:
            dataframe = pl.DataFrame()
        
        # Create PDF with error handling
        pdf = PDFReport()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        try:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "1. Executive AI Summary")
            pdf.set_font("Helvetica", size=11)
            # Limit summary length to prevent PDF rendering issues
            safe_summary = str(ai_summary)[:5000]
            pdf.multi_cell(0, 8, safe_summary)
        except Exception as e:
            logger.error(f"Error adding summary to PDF: {e}")
            pdf.set_font("Helvetica", size=10)
            pdf.cell(0, 10, f"Summary rendering failed: {str(e)[:100]}")
        
        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "2. Cleaned Data Sample")

        sample_df = dataframe.head(10)
        if sample_df.columns and sample_df.height > 0:
            column_count = len(sample_df.columns)
            if column_count > 0:
                try:
                    col_width = max(5, pdf.epw / column_count)  # Ensure col_width is reasonable

                    pdf.set_font("Helvetica", "B", 9)
                    for column_name in sample_df.columns:
                        safe_col = str(column_name)[:50]
                        pdf.cell(col_width, 8, safe_col, border=1)
                    pdf.ln(8)

                    pdf.set_font("Helvetica", size=8)
                    for row in sample_df.iter_rows():
                        for item in row:
                            safe_item = str(item)[:100]
                            pdf.cell(col_width, 8, safe_item, border=1)
                        pdf.ln(8)
                except Exception as e:
                    logger.error(f"Error adding table to PDF: {e}")
                    pdf.set_font("Helvetica", size=10)
                    pdf.cell(0, 10, f"Table rendering failed: {str(e)[:100]}")
        else:
            pdf.set_font("Helvetica", size=10)
            pdf.cell(0, 8, "No rows available.")

        return _pdf_output_bytes(pdf)
    
    except Exception as e:
        # Create minimal fallback PDF on error
        logger.exception(f"Failed to generate PDF: {e}")
        try:
            fallback_pdf = PDFReport()
            fallback_pdf.add_page()
            fallback_pdf.set_font("Helvetica", size=11)
            fallback_pdf.cell(0, 10, f"PDF generation failed: {str(e)[:200]}")
            return _pdf_output_bytes(fallback_pdf)
        except Exception as fallback_error:
            logger.exception(f"Even fallback PDF failed: {fallback_error}")
            # Return minimal valid PDF
            return b"%PDF-1.4\n%EOF"
