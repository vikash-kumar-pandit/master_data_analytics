import polars as pl
from fpdf import FPDF


class PDFReport(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "Automated Big Data Analysis Report", align="C", ln=True)
        self.ln(5)


def create_pdf_in_memory(ai_summary: str, dataframe: pl.DataFrame) -> bytes:
    pdf = PDFReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "1. Executive AI Summary", ln=True)
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 8, ai_summary)
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "2. Cleaned Data Sample", ln=True)

    sample_df = dataframe.head(10)
    if sample_df.columns:
        column_count = len(sample_df.columns)
        col_width = pdf.epw / column_count

        pdf.set_font("Helvetica", "B", 9)
        for column_name in sample_df.columns:
            pdf.cell(col_width, 8, str(column_name), border=1)
        pdf.ln(8)

        pdf.set_font("Helvetica", size=8)
        for row in sample_df.iter_rows():
            for item in row:
                pdf.cell(col_width, 8, str(item), border=1)
            pdf.ln(8)
    else:
        pdf.set_font("Helvetica", size=10)
        pdf.cell(0, 8, "No rows available.", ln=True)

    output = pdf.output(dest="S")
    if isinstance(output, bytes):
        return output
    return output.encode("latin-1")
