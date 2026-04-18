import io
import polars as pl
from fpdf import FPDF
from pptx import Presentation
from pptx.util import Inches, Pt


class PDFTable(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, getattr(self, "report_title", "Data Analysis Report"), border=False, ln=True, align="C")
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
    if isinstance(pdf_output, (bytes, bytearray)):
        return bytes(pdf_output)
    return pdf_output.encode("latin-1")


def generate_structured_report_pdf(*, title: str, subtitle: str, sections: list[dict]) -> bytes:
    pdf = PDFTable()
    pdf.report_title = title
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, title, ln=True)
    pdf.cell(0, 10, subtitle, ln=True)
    pdf.ln(4)

    for section in sections:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 9, str(section.get("heading") or "Section"), ln=True)
        pdf.set_font("Helvetica", size=10)
        rows = section.get("rows") or []
        for row in rows:
            label = str(row.get("label") or "")
            value = str(row.get("value") or "")
            pdf.multi_cell(0, 7, f"{label}: {value}")
        pdf.ln(2)

    pdf_output = pdf.output(dest="S")
    if isinstance(pdf_output, (bytes, bytearray)):
        return bytes(pdf_output)
    return pdf_output.encode("latin-1")


def generate_structured_report_pptx(*, title: str, subtitle: str, sections: list[dict]) -> bytes:
    presentation = Presentation()
    presentation.slide_width = Inches(13.333)
    presentation.slide_height = Inches(7.5)

    title_slide_layout = presentation.slide_layouts[0]
    title_slide = presentation.slides.add_slide(title_slide_layout)
    title_slide.shapes.title.text = title
    title_slide.placeholders[1].text = subtitle

    for section in sections:
        slide_layout = presentation.slide_layouts[1]
        slide = presentation.slides.add_slide(slide_layout)
        slide.shapes.title.text = str(section.get("heading") or "Section")

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
            label = str(row.get("label") or "")
            value = str(row.get("value") or "")
            paragraph = body.paragraphs[0] if first_row else body.add_paragraph()
            paragraph.text = f"{label}: {value}"
            paragraph.level = 0
            paragraph.font.size = Pt(18)
            first_row = False

    output = io.BytesIO()
    presentation.save(output)
    return output.getvalue()
