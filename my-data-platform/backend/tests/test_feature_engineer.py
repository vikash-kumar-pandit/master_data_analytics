import polars as pl
from datetime import datetime
from feature_engineer import auto_feature_engineer

def test_auto_feature_engineer_datetime():
    # Create a dummy dataframe with date column
    df = pl.DataFrame({
        "timestamp": [datetime(2026, 7, 8, 12, 0), datetime(2026, 7, 12, 12, 0)] # Wed and Sun
    })
    
    res_df, notes = auto_feature_engineer(df)
    
    assert "timestamp_Year" in res_df.columns
    assert "timestamp_Month" in res_df.columns
    assert "timestamp_Weekday" in res_df.columns
    assert "timestamp_Is_Weekend" in res_df.columns
    
    # 2026-07-08 is Wednesday (weekday 3), 2026-07-12 is Sunday (weekday 7)
    assert res_df["timestamp_Is_Weekend"].to_list() == [0, 1]
    assert len(notes) == 1

def test_auto_feature_engineer_text():
    # Create a dummy dataframe with text column
    df = pl.DataFrame({
        "reviews": [
            "This is a long feedback review meant to trigger text analytics length feature!",
            "Short feedback review text length is also quite long to keep average length high."
        ]
    })
    
    res_df, notes = auto_feature_engineer(df)
    assert "reviews_Length" in res_df.columns
    assert "reviews_Punctuation_Count" in res_df.columns
    assert res_df["reviews_Punctuation_Count"].to_list() == [1, 0]
    assert len(notes) == 1

def test_auto_feature_engineer_financial():
    # Create a dummy dataframe with sales and cost
    df = pl.DataFrame({
        "sales": [100.0, 200.0, 0.0],
        "cost": [70.0, 150.0, 10.0]
    })
    
    res_df, notes = auto_feature_engineer(df)
    assert "Auto_Profit_Margin_Ratio" in res_df.columns
    
    # Profit margins: (100-70)/100 = 0.3, (200-150)/200 = 0.25, (0-10)/1 = -10
    assert res_df["Auto_Profit_Margin_Ratio"].to_list() == [0.3, 0.25, -10.0]
    assert len(notes) == 1
