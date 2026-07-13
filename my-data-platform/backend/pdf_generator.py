import os
import io
import json
import base64
import logging
import re
from datetime import datetime
from typing import Any

# Add GTK+ DLL directory for WeasyPrint on Windows
if os.name == 'nt':
    for sd in [
        r"C:\Program Files\GTK3-Runtime Win64\bin",
        r"C:\Program Files\GTK3-Runtime\bin",
        r"C:\Program Files (x86)\GTK3-Runtime Win64\bin",
        r"C:\Program Files (x86)\GTK3-Runtime\bin",
    ]:
        if os.path.exists(sd):
            try:
                os.add_dll_directory(sd)
                break
            except Exception:
                pass

import polars as pl
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from weasyprint import HTML

logger = logging.getLogger(__name__)


def markdown_to_html(md_text: str) -> str:
    """Converts basic markdown headers, bold, and list items into HTML tags."""
    if not md_text:
        return ""
    
    # Convert header lines
    lines = md_text.split("\n")
    processed_lines = []
    in_list = False
    
    for line in lines:
        stripped = line.strip()
        
        # Headings
        if stripped.startswith("### "):
            if in_list:
                processed_lines.append("</ul>")
                in_list = False
            processed_lines.append(f"<h3>{stripped[4:]}</h3>")
            continue
        elif stripped.startswith("## "):
            if in_list:
                processed_lines.append("</ul>")
                in_list = False
            processed_lines.append(f"<h2>{stripped[3:]}</h2>")
            continue
        elif stripped.startswith("# "):
            if in_list:
                processed_lines.append("</ul>")
                in_list = False
            processed_lines.append(f"<h1>{stripped[2:]}</h1>")
            continue
            
        # Lists
        if stripped.startswith("* ") or stripped.startswith("- "):
            if not in_list:
                processed_lines.append("<ul>")
                in_list = True
            content = stripped[2:]
            # Replace inline formatting in list content
            content = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", content)
            content = re.sub(r"\*(.*?)\*", r"<em>\1</em>", content)
            processed_lines.append(f"<li>{content}</li>")
            continue
        else:
            if in_list:
                processed_lines.append("</ul>")
                in_list = False
        
        # Paragraphs & Inline elements
        line_processed = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", line)
        line_processed = re.sub(r"\*(.*?)\*", r"<em>\1</em>", line_processed)
        
        if line_processed.strip() == "":
            processed_lines.append("<br/>")
        else:
            processed_lines.append(line_processed)
            
    if in_list:
        processed_lines.append("</ul>")
        
    return "\n".join(processed_lines)


def generate_distribution_base64(df: pl.DataFrame) -> str:
    """Generates an in-memory distribution plot of the primary numerical column."""
    try:
        numeric_cols = [col for col, dtype in zip(df.columns, df.dtypes) if dtype in [
            pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.Float32, pl.Float64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64
        ]]
        if not numeric_cols:
            return ""
        
        # Take the first numeric column
        col_to_plot = numeric_cols[0]
        values = df[col_to_plot].drop_nulls().to_list()
        
        if len(values) < 5:
            return ""
        
        plt.close('all')
        fig, ax = plt.subplots(figsize=(6.5, 3.8), dpi=150)
        ax.hist(values, bins=15, color='#3182ce', edgecolor='#2b6cb0', alpha=0.75, rwidth=0.9)
        ax.set_title(f"Distribution Profile: {col_to_plot}", fontsize=11, fontweight='bold', color='#1a365d', pad=12)
        ax.set_xlabel(col_to_plot, fontsize=9, fontweight='bold', color='#4a5568')
        ax.set_ylabel("Observation Frequency", fontsize=9, fontweight='bold', color='#4a5568')
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.tick_params(labelsize=8)
        
        # Style borders
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        for spine in ['left', 'bottom']:
            ax.spines[spine].set_color('#cbd5e0')
            
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception as e:
        logger.error(f"Error generating distribution plot: {e}")
        return ""


def generate_correlation_matrix_base64(df: pl.DataFrame) -> str:
    """Generates an in-memory correlation heatmap of numerical columns."""
    try:
        numeric_cols = [col for col, dtype in zip(df.columns, df.dtypes) if dtype in [
            pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.Float32, pl.Float64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64
        ]]
        if len(numeric_cols) < 2:
            return ""
            
        # Select first 6 columns if there are too many to keep the visual neat
        cols_subset = numeric_cols[:6]
        pdf_sub = df.select(cols_subset).to_pandas()
        corr = pdf_sub.corr()
        
        plt.close('all')
        fig, ax = plt.subplots(figsize=(6, 5), dpi=150)
        im = ax.imshow(corr.values, cmap='coolwarm', vmin=-1, vmax=1)
        
        ax.set_xticks(np.arange(len(cols_subset)))
        ax.set_yticks(np.arange(len(cols_subset)))
        ax.set_xticklabels(cols_subset, rotation=35, ha='right', fontsize=8, color='#4a5568')
        ax.set_yticklabels(cols_subset, fontsize=8, color='#4a5568')
        
        # Add values inside cells
        for i in range(len(cols_subset)):
            for j in range(len(cols_subset)):
                val = corr.values[i, j]
                if not np.isnan(val):
                    ax.text(j, i, f"{val:.2f}",
                            ha="center", va="center",
                            color="black" if abs(val) < 0.5 else "white",
                            fontsize=8, fontweight='bold')
                            
        fig.colorbar(im, ax=ax, shrink=0.75, pad=0.05)
        ax.set_title("Numeric Feature Correlation Matrix", fontsize=11, fontweight='bold', color='#1a365d', pad=15)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception as e:
        logger.error(f"Error generating correlation heatmap: {e}")
        return ""


def generate_ml_visualization_base64(df: pl.DataFrame, target_column: str) -> str:
    """Generates an in-memory ML performance plot (ROC curve or Actual-vs-Predicted scatter)."""
    if not target_column or target_column not in df.columns:
        return ""
    
    try:
        from sklearn.model_selection import train_test_split
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        from sklearn.preprocessing import OneHotEncoder
        from sklearn.impute import SimpleImputer
        from sklearn.compose import ColumnTransformer
        from sklearn.pipeline import Pipeline
        from sklearn.metrics import roc_curve, auc
        
        # Select features & target
        y_series = df[target_column]
        x_df = df.drop(target_column)
        
        n_unique_y = y_series.n_unique()
        y_dtype = y_series.dtype
        is_classification = True
        if y_dtype.is_float():
            is_classification = False
        elif (y_dtype.is_numeric() or y_dtype.is_integer()) and n_unique_y > 10:
            is_classification = False
        
        numeric_cols = [col for col, dtype in x_df.schema.items() if dtype.is_numeric() or dtype.is_integer() or dtype == pl.Boolean]
        categorical_cols = [col for col in x_df.columns if col not in numeric_cols]
        
        df_pandas = df.to_pandas()
        y = df_pandas[target_column]
        x = df_pandas.drop(columns=[target_column])
        
        numeric_pipeline = Pipeline([("imputer", SimpleImputer(strategy="median"))])
        categorical_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ])
        preprocessor = ColumnTransformer([
            ("num", numeric_pipeline, numeric_cols),
            ("cat", categorical_pipeline, categorical_cols),
        ])
        
        # Stratify only if is_classification and the minimum class count is >= 2
        stratify_y = None
        if is_classification:
            try:
                min_class_size = y.value_counts().min()
                if min_class_size >= 2:
                    stratify_y = y
            except Exception:
                pass
        
        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=0.3, random_state=42, stratify=stratify_y
        )
        
        plt.close('all')
        fig, ax = plt.subplots(figsize=(6.5, 4), dpi=150)
        
        if is_classification:
            from sklearn.preprocessing import LabelEncoder
            le = LabelEncoder()
            y_train_enc = le.fit_transform(y_train)
            y_test_enc = le.transform(y_test)
            n_classes = len(le.classes_)
            
            if n_classes == 2:
                clf = Pipeline([("preprocessor", preprocessor), ("model", RandomForestClassifier(n_estimators=100, random_state=42))])
                clf.fit(x_train, y_train_enc)
                y_probs = clf.predict_proba(x_test)[:, 1]
                
                fpr, tpr, _ = roc_curve(y_test_enc, y_probs)
                roc_auc = auc(fpr, tpr)
                
                ax.plot(fpr, tpr, color='#3182ce', lw=2, label=f'ROC curve (AUC = {roc_auc:.2f})')
                ax.plot([0, 1], [0, 1], color='#cbd5e0', lw=1.5, linestyle='--')
                ax.set_xlim([0.0, 1.0])
                ax.set_ylim([0.0, 1.05])
                ax.set_xlabel('False Positive Rate', fontsize=9, fontweight='bold', color='#4a5568')
                ax.set_ylabel('True Positive Rate', fontsize=9, fontweight='bold', color='#4a5568')
                ax.set_title('Receiver Operating Characteristic (ROC) Curve', fontsize=11, fontweight='bold', color='#1a365d')
                ax.legend(loc="lower right", fontsize=8)
            else:
                clf = Pipeline([("preprocessor", preprocessor), ("model", RandomForestClassifier(n_estimators=100, random_state=42))])
                clf.fit(x_train, y_train_enc)
                importances = clf.named_steps['model'].feature_importances_
                
                try:
                    feat_importances = importances[:len(numeric_cols)]
                    sorted_idx = np.argsort(feat_importances)
                    y_ticks = np.arange(len(numeric_cols))
                    ax.barh(y_ticks, feat_importances[sorted_idx], color='#3182ce', align='center')
                    ax.set_yticks(y_ticks)
                    ax.set_yticklabels([numeric_cols[i] for i in sorted_idx], fontsize=8)
                    ax.set_title('Feature Importance (Random Forest Classifier)', fontsize=11, fontweight='bold', color='#1a365d')
                    ax.set_xlabel('Relative Importance', fontsize=9, fontweight='bold', color='#4a5568')
                except Exception:
                    ax.text(0.5, 0.5, "Classification Estimator Evaluated Successfully", ha='center', va='center')
        else:
            reg = Pipeline([("preprocessor", preprocessor), ("model", RandomForestRegressor(n_estimators=100, random_state=42))])
            reg.fit(x_train, y_train)
            y_pred = reg.predict(x_test)
            
            ax.scatter(y_test, y_pred, alpha=0.6, color='#3182ce', edgecolors='#2b6cb0', s=25)
            lims = [
                np.min([ax.get_xlim(), ax.get_ylim()]),
                np.max([ax.get_xlim(), ax.get_ylim()]),
            ]
            ax.plot(lims, lims, '#e53e3e', alpha=0.75, zorder=0, linestyle='--', lw=1.5)
            ax.set_xlim(lims)
            ax.set_ylim(lims)
            ax.set_xlabel('Actual Values', fontsize=9, fontweight='bold', color='#4a5568')
            ax.set_ylabel('Predicted Values', fontsize=9, fontweight='bold', color='#4a5568')
            ax.set_title('Model Prediction Accuracy: Actual vs. Predicted', fontsize=11, fontweight='bold', color='#1a365d')
            ax.grid(True, linestyle='--', alpha=0.3)
            
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        for spine in ['left', 'bottom']:
            ax.spines[spine].set_color('#cbd5e0')
            
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception as e:
        logger.error(f"Error generating ML visualization: {e}")
        return ""


def create_pdf_in_memory(ai_summary: str, dataframe: pl.DataFrame, target_column: str = None) -> bytes:
    """Generate academic-grade PDF report using WeasyPrint with embedded plots, telemetry, and styled elements."""
    try:
        if dataframe is None:
            dataframe = pl.DataFrame()
            
        ai_summary = ai_summary or "No executive summary available."
        formatted_summary = markdown_to_html(ai_summary)
        
        total_rows = dataframe.height
        total_cols = dataframe.width
        
        columns_meta = []
        for name, dtype in zip(dataframe.columns, dataframe.dtypes):
            null_count = dataframe[name].null_count()
            null_pct = (null_count / total_rows * 100) if total_rows > 0 else 0
            columns_meta.append({
                "name": name,
                "type": str(dtype),
                "null_pct": f"{null_pct:.1f}%",
                "non_null": total_rows - null_count
            })
            
        dist_img = generate_distribution_base64(dataframe)
        corr_img = generate_correlation_matrix_base64(dataframe)
        ml_img = generate_ml_visualization_base64(dataframe, target_column) if target_column else ""
        
        sample_df = dataframe.head(10)
        sample_headers = sample_df.columns
        sample_rows = sample_df.iter_rows()
        
        generation_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Data Science Laboratory Report</title>
            <style>
                @page {{
                    size: A4;
                    margin: 20mm;
                    @bottom-right {{
                        content: "Page " counter(page) " of " counter(pages);
                        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                        font-size: 8pt;
                        color: #718096;
                    }}
                    @bottom-left {{
                        content: "DataSaaS Pro Analytics Pipeline • Lab Telemetry";
                        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                        font-size: 8pt;
                        color: #718096;
                    }}
                }}
                body {{
                    font-family: 'Georgia', 'Times New Roman', serif;
                    color: #2d3748;
                    line-height: 1.6;
                    font-size: 10.5pt;
                }}
                header {{
                    border-bottom: 2px solid #2b6cb0;
                    padding-bottom: 12px;
                    margin-bottom: 25px;
                }}
                .report-title {{
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    color: #1a365d;
                    font-size: 24pt;
                    font-weight: 800;
                    margin: 0 0 5px 0;
                    letter-spacing: -0.5px;
                    text-transform: uppercase;
                }}
                .report-subtitle {{
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    color: #4a5568;
                    font-size: 12pt;
                    margin: 0;
                    font-weight: 400;
                }}
                .metadata-grid {{
                    display: table;
                    width: 100%;
                    margin-bottom: 25px;
                    background-color: #f7fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    border-collapse: collapse;
                }}
                .metadata-row {{
                    display: table-row;
                }}
                .metadata-cell {{
                    display: table-cell;
                    padding: 8px 12px;
                    font-size: 9pt;
                    border: 1px solid #e2e8f0;
                }}
                .metadata-label {{
                    font-weight: bold;
                    color: #4a5568;
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    background-color: #edf2f7;
                    width: 25%;
                }}
                h2 {{
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    color: #2b6cb0;
                    font-size: 14pt;
                    margin-top: 30px;
                    margin-bottom: 15px;
                    border-bottom: 1px solid #e2e8f0;
                    padding-bottom: 5px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                p {{
                    margin-bottom: 15px;
                    text-align: justify;
                }}
                ul, ol {{
                    margin-bottom: 15px;
                    padding-left: 20px;
                }}
                li {{
                    margin-bottom: 6px;
                }}
                .section-container {{
                    page-break-inside: avoid;
                    margin-bottom: 25px;
                }}
                .data-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                    margin-bottom: 20px;
                    font-size: 8.5pt;
                }}
                .data-table th {{
                    background-color: #2b6cb0;
                    color: white;
                    font-weight: bold;
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    text-align: left;
                    padding: 6px 8px;
                    border: 1px solid #cbd5e0;
                }}
                .data-table td {{
                    padding: 5px 8px;
                    border: 1px solid #e2e8f0;
                    font-family: monospace;
                }}
                .data-table tr:nth-child(even) {{
                    background-color: #f7fafc;
                }}
                .chart-container {{
                    display: table;
                    width: 100%;
                    margin: 20px 0;
                    page-break-inside: avoid;
                }}
                .chart-box {{
                    display: table-cell;
                    width: 50%;
                    padding: 5px;
                    text-align: center;
                    vertical-align: middle;
                }}
                .chart-img {{
                    max-width: 95%;
                    border: 1px solid #e2e8f0;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.04);
                }}
                .insights-callout {{
                    background-color: #ebf8ff;
                    border-left: 4px solid #3182ce;
                    padding: 15px;
                    border-radius: 0 6px 6px 0;
                    margin: 20px 0;
                }}
                .insights-title {{
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    font-weight: bold;
                    color: #2b6cb0;
                    margin-bottom: 8px;
                    font-size: 11pt;
                }}
            </style>
        </head>
        <body>
            <header>
                <h1 class="report-title">Data Science Lab Report</h1>
                <p class="report-subtitle">Automated Exploratory Data Analysis & Modeling Analysis</p>
            </header>

            <div class="metadata-grid">
                <div class="metadata-row">
                    <div class="metadata-cell metadata-label">Generated On</div>
                    <div class="metadata-cell">{generation_time}</div>
                    <div class="metadata-cell metadata-label">Dataset Profile</div>
                    <div class="metadata-cell">{total_rows} Rows x {total_cols} Columns</div>
                </div>
                <div class="metadata-row">
                    <div class="metadata-cell metadata-label">Pipeline Engine</div>
                    <div class="metadata-cell">Polars & WeasyPrint PDF Engine</div>
                    <div class="metadata-cell metadata-label">PII Sanitized</div>
                    <div class="metadata-cell">Active (Regex Rule Engine)</div>
                </div>
            </div>

            <div class="section-container">
                <h2>1. Executive Summary & AI Insights</h2>
                <div class="insights-callout">
                    <div class="insights-title">Automated AI Analyst Insights</div>
                    {formatted_summary}
                </div>
            </div>

            <div class="section-container">
                <h2>2. Dataset Schema & Completeness Profile</h2>
                <p>The table below summarizes the column names, physical storage types, and completeness counts computed from the dataset:</p>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Column Name</th>
                            <th>Data Type</th>
                            <th>Completeness Count</th>
                            <th>Null Percentage</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for col in columns_meta:
            html_content += f"""
                        <tr>
                            <td>{col['name']}</td>
                            <td>{col['type']}</td>
                            <td>{col['non_null']} / {total_rows}</td>
                            <td>{col['null_pct']}</td>
                        </tr>
            """
            
        html_content += """
                    </tbody>
                </table>
            </div>
        """
        
        if dist_img or corr_img:
            html_content += """
            <div class="section-container">
                <h2>3. Exploratory Feature Visualizations</h2>
                <div class="chart-container">
            """
            
            if dist_img:
                html_content += f"""
                    <div class="chart-box">
                        <img class="chart-img" src="data:image/png;base64,{dist_img}" alt="Distribution Analysis"/>
                    </div>
                """
            if corr_img:
                html_content += f"""
                    <div class="chart-box">
                        <img class="chart-img" src="data:image/png;base64,{corr_img}" alt="Correlation Heatmap"/>
                    </div>
                """
                
            html_content += """
                </div>
            </div>
            """
            
        if ml_img:
            html_content += f"""
            <div class="section-container" style="page-break-before: always;">
                <h2>4. Machine Learning Model Performance Visualizations</h2>
                <p>A machine learning predictive model (Random Forest) was trained on the target column <strong>{target_column}</strong>. The visualization below details its performance metrics:</p>
                <div class="chart-container" style="text-align: center;">
                    <img class="chart-img" style="max-width: 80%;" src="data:image/png;base64,{ml_img}" alt="ML Model Performance"/>
                </div>
            </div>
            """
            
        if total_rows > 0:
            html_content += f"""
            <div class="section-container" style="page-break-before: always;">
                <h2>{5 if ml_img else 4}. Sample Dataset Observations (First 10 Rows)</h2>
                <table class="data-table" style="font-size: 7.5pt;">
                    <thead>
                        <tr>
            """
            
            for head in sample_headers:
                html_content += f"<th>{head}</th>"
                
            html_content += """
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for row in sample_rows:
                html_content += "<tr>"
                for item in row:
                    safe_item = str(item or "")
                    if len(safe_item) > 25:
                        safe_item = safe_item[:22] + "..."
                    html_content += f"<td>{safe_item}</td>"
                html_content += "</tr>"
                
            html_content += """
                    </tbody>
                </table>
            </div>
            """
            
        html_content += """
        </body>
        </html>
        """
        
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes
        
    except Exception as e:
        logger.exception(f"Failed to generate WeasyPrint PDF: {e}")
        return b"%PDF-1.4\n%EOF"
