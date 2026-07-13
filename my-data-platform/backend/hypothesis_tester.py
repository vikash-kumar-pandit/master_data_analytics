import logging
from typing import Any
import polars as pl
from scipy import stats
import numpy as np

logger = logging.getLogger("hypothesis_tester")

def run_automated_ab_test(
    dataframe: pl.DataFrame, 
    metric_col: str, 
    category_col: str
) -> dict[str, Any]:
    """
    Automatically performs a T-Test between the top 2 categories of a dataset
    and returns a business-friendly, plain English explanation.
    """
    try:
        # 1. डेटा वैलिडेशन: चेक करें कि क्या कॉलम्स मौजूद हैं
        if metric_col not in dataframe.columns or category_col not in dataframe.columns:
            return {"error": "Metric or Category column not found in dataset."}
            
        # 2. खाली वैल्यूज (Nulls) को हटाएं
        df_clean = dataframe.select([metric_col, category_col]).drop_nulls()
        
        # 3. टॉप 2 कैटेगरी (Groups) खोजें
        top_categories = (
            df_clean.group_by(category_col)
            .len()
            .sort("len", descending=True)
            .head(2)[category_col]
            .to_list()
        )
        
        if len(top_categories) < 2:
            return {"error": "Not enough categories to compare. Need at least 2."}
            
        group_a_name = top_categories[0]
        group_b_name = top_categories[1]
        
        # 4. दोनों ग्रुप्स का डेटा अलग-अलग NumPy arrays में निकालें (Speed के लिए)
        group_a_data = df_clean.filter(pl.col(category_col) == group_a_name)[metric_col].to_numpy()
        group_b_data = df_clean.filter(pl.col(category_col) == group_b_name)[metric_col].to_numpy()
        
        if len(group_a_data) < 30 or len(group_b_data) < 30:
            return {"warning": "Sample size is too small (<30) for a highly reliable statistical test."}
            
        # 5. Statistical T-Test (Welch's T-Test) रन करें
        t_stat, p_value = stats.ttest_ind(group_a_data, group_b_data, equal_var=False)
        
        # 6. मीन्स (Averages) कैलकुलेट करें
        mean_a = np.mean(group_a_data)
        mean_b = np.mean(group_b_data)
        
        # 7. AI की तरह बिज़नेस-फ्रेंडली इनसाइट (Plain English) जनरेट करें
        is_significant = p_value < 0.05
        better_group = group_a_name if mean_a > mean_b else group_b_name
        percentage_diff = abs((mean_a - mean_b) / min(mean_a, mean_b)) * 100 if min(mean_a, mean_b) != 0 else 0
        
        if is_significant:
            insight = (
                f"🚀 Statistically Proven: '{better_group}' is performing {percentage_diff:.1f}% better "
                f"than the other group in terms of {metric_col}. "
                f"With a p-value of {p_value:.4f} (< 0.05), we are 95% confident this is a real business trend, not just random luck."
            )
        else:
            insight = (
                f"⚖️ No Clear Winner: Although there is a {percentage_diff:.1f}% difference in {metric_col}, "
                f"our statistical test (p-value {p_value:.4f} > 0.05) shows this difference is likely due to random chance. "
                f"We recommend collecting more data before making a major business decision."
            )
            
        return {
            "status": "success",
            "metric": metric_col,
            "group_a": {"name": str(group_a_name), "average": float(mean_a), "sample_size": len(group_a_data)},
            "group_b": {"name": str(group_b_name), "average": float(mean_b), "sample_size": len(group_b_data)},
            "p_value": float(p_value),
            "is_statistically_significant": bool(is_significant),
            "business_insight": insight
        }
        
    except Exception as e:
        logger.exception(f"Automated Hypothesis Test failed: {e}")
        return {"error": f"Testing failed: {str(e)}"}
