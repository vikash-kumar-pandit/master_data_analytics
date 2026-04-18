import polars as pl
from fpdf import FPDF


class PDFTable(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "Data Analysis & Cleaning Report", border=False, ln=True, align="C")
        self.ln(10)


def generate_pdf_in_memory(dataframe: pl.DataFrame, analysis_summary: dict) -> bytes:
    pdf = PDFTable()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, f"Total Rows Processed: {analysis_summary.get('rows', 0)}", ln=True)
    pdf.cell(0, 10, f"Data Category Detected: {analysis_summary.get('category', 'Unknown')}", ln=True)
    pdf.cell(0, 10, f"Columns Detected: {analysis_summary.get('cols', 0)}", ln=True)
    pdf.ln(8)

    sample_dataframe = dataframe.head(20)

    if sample_dataframe.columns:
        column_count = len(sample_dataframe.columns)
        col_width = pdf.epw / column_count

        pdf.set_font("Helvetica", "B", 10)
        for column_name in sample_dataframe.columns:
            pdf.cell(col_width, 8, str(column_name), border=1)
        pdf.ln(8)

        pdf.set_font("Helvetica", size=9)
        for values in sample_dataframe.iter_rows():
            for value in values:
                pdf.cell(col_width, 8, str(value), border=1)
            pdf.ln(8)
    else:
        pdf.set_font("Helvetica", size=10)
        pdf.cell(0, 10, "No tabular columns were available to render.", ln=True)

    pdf_output = pdf.output(dest="S")
    if isinstance(pdf_output, bytes):
        return pdf_output
    return pdf_output.encode("latin-1")
