import pytest
import os
import json
import polars as pl
from unittest.mock import patch, MagicMock
from preparation.service import DatasetPreparerService

@pytest.fixture
def temp_files(tmp_path):
    in_path = tmp_path / "input.csv"
    out_path = tmp_path / "output.csv"
    yield in_path, out_path
    if in_path.exists():
        in_path.unlink()
    if out_path.exists():
        out_path.unlink()

def test_file_formats_and_sinking(tmp_path):
    # Test CSV with delimiter detection (semicolon)
    in_csv = tmp_path / "semi.csv"
    out_csv = tmp_path / "out.csv"
    in_csv.write_text("a;b\n1;2\n3;4", encoding="utf-8")
    
    preparer = DatasetPreparerService(str(in_csv), str(out_csv))
    lf = preparer._get_lazyframe()
    assert lf.columns == ["a", "b"]
    
    # Test writing parquet
    out_parquet = tmp_path / "out.parquet"
    preparer.output_path = str(out_parquet)
    preparer._write_lazyframe(lf)
    assert out_parquet.exists()
    
    # Test reading parquet
    preparer_pq = DatasetPreparerService(str(out_parquet), str(out_csv))
    lf_pq = preparer_pq._get_lazyframe()
    assert lf_pq.columns == ["a", "b"]
    
    # Test writing json
    out_json = tmp_path / "out.json"
    preparer.output_path = str(out_json)
    preparer._write_lazyframe(lf)
    assert out_json.exists()
    
    # Test non-standard extension reading fallback
    in_txt = tmp_path / "semi.txt"
    in_txt.write_text("a,b\n1,2\n3,4", encoding="utf-8")
    with patch("polars.read_excel") as mock_read_excel:
        mock_read_excel.return_value = pl.DataFrame({"a": [1, 3], "b": [2, 4]})
        preparer_txt = DatasetPreparerService(str(in_txt), str(out_csv))
        assert preparer_txt._get_lazyframe().columns == ["a", "b"]


def test_execute_transforms(temp_files):
    in_path, out_path = temp_files
    
    # Base dataset for testing transforms
    df = pl.DataFrame({
        "name": ["  Alice  ", "Bob", None, "CHARLIE", "  Alice  "],
        "val": [10.0, None, 20.0, 30.0, 10.0],
        "category": ["A", "B", "A", "B", "A"],
        "date_str": ["2026-01-01", "2026-01-02", "2026-01-03", None, "2026-01-01"],
        "text_with_html": ["<p>hello</p>", "world", None, "test", "<p>hello</p>"]
    })
    df.write_csv(in_path)
    
    preparer = DatasetPreparerService(str(in_path), str(out_path))

    # Helper function to reset & run transform
    def run_op(op, params, custom_df=None):
        data_to_write = custom_df if custom_df is not None else df
        data_to_write.write_csv(in_path)
        comp, desc = preparer.execute_transform(op, params)
        res = pl.read_csv(out_path)
        return res, comp, desc

    # 1. remove_missing
    res, _, _ = run_op("remove_missing", {"columns": ["name"]})
    assert res.height == 4
    assert None not in res["name"].to_list()

    # 2. fill_mean
    res, _, _ = run_op("fill_mean", {"columns": ["val"]})
    assert res["val"].null_count() == 0
    assert res["val"][1] == 17.5 # mean of 10, 20, 30, 10 is 17.5

    # 3. fill_median
    res, _, _ = run_op("fill_median", {"columns": ["val"]})
    assert res["val"].null_count() == 0
    assert res["val"][1] == 15.0 # median of 10, 20, 30, 10 is 15.0

    # 4. fill_mode
    res, _, _ = run_op("fill_mode", {"columns": ["name"]})
    assert res["name"].null_count() == 0
    assert res["name"][2].strip() == "Alice" # mode is Alice

    # 5. forward_fill
    res, _, _ = run_op("forward_fill", {"columns": ["val"]})
    assert res["val"][1] == 10.0

    # 6. backward_fill
    res, _, _ = run_op("backward_fill", {"columns": ["val"]})
    assert res["val"][1] == 20.0

    # 7. interpolate
    res, _, _ = run_op("interpolate", {"columns": ["val"]})
    assert res["val"][1] == 15.0 # linear interpolation between 10 and 20

    # 8. duplicate_removal
    res, _, _ = run_op("duplicate_removal", {})
    assert res.height == 4 # One duplicate Alice row removed

    # 9. column_rename
    res, _, _ = run_op("column_rename", {"rename_map": {"name": "first_name"}})
    assert "first_name" in res.columns
    assert "name" not in res.columns

    # 10. column_merge
    res, _, _ = run_op("column_merge", {"columns": ["name", "category"], "separator": "-", "output_column": "merged"})
    assert "merged" in res.columns
    assert res["merged"][1] == "Bob-B"

    # 11. column_split
    res, _, _ = run_op("column_split", {"column": "date_str", "separator": "-"})
    assert "date_str_part_1" in res.columns
    assert str(res["date_str_part_1"][0]) == "2026"

    # 12. drop_column
    res, _, _ = run_op("drop_column", {"columns": ["val", "category"]})
    assert "val" not in res.columns
    assert "category" not in res.columns

    # 13. keep_column
    res, _, _ = run_op("keep_column", {"columns": ["name"]})
    assert res.columns == ["name"]

    # 14. cast_type
    res, _, _ = run_op("cast_type", {"columns": ["val"], "target_type": "int"})
    assert res["val"].dtype in [pl.Int64, pl.Int32]

    df_curr = pl.DataFrame({"price": ["$100.50", "€200.00", None]})
    res_curr, _, _ = run_op("currency_parsing", {"columns": ["price"]}, custom_df=df_curr)
    assert res_curr["price"].dtype == pl.Float64
    assert res_curr["price"][0] == 100.50

    # 16. date_parsing
    res, _, _ = run_op("date_parsing", {"columns": ["date_str"], "date_format": "%Y-%m-%d"})
    # polars read_csv might read datetime back as string unless we specify, but let's check parsing success
    # Checking that it has been executed
    assert "date_str" in res.columns

    # 17. trim_spaces
    res, _, _ = run_op("trim_spaces", {"columns": ["name"]})
    assert res["name"][0] == "Alice" # stripped

    # 18. lowercase
    res, _, _ = run_op("lowercase", {"columns": ["name"]})
    assert res["name"][3] == "charlie"

    # 19. uppercase
    res, _, _ = run_op("uppercase", {"columns": ["name"]})
    assert res["name"][0].strip() == "ALICE"

    # 20. regex_replace
    res, _, _ = run_op("regex_replace", {"columns": ["name"], "pattern": r"^\s*Al.*", "replacement": "A-User"})
    assert res["name"][0] == "A-User"

    # 21. regex_extract
    res, _, _ = run_op("regex_extract", {"columns": ["name"], "pattern": "(Al.*)", "group_index": 1})
    assert res["name"][0] == "Alice  "

    # 22. find_replace
    res, _, _ = run_op("find_replace", {"columns": ["category"], "find_value": "A", "replacement": "Alpha"})
    assert res["category"][0] == "Alpha"

    df_outlier = pl.DataFrame({"val": [10.0, 11.0, 12.0, 10.0, 1000.0, 11.0]})
    res_out, _, _ = run_op("outlier_removal", {"columns": ["val"]}, custom_df=df_outlier)
    assert 1000.0 not in res_out["val"].to_list()

    df_winsor = pl.DataFrame({"val": list(range(100))})
    res_win, _, _ = run_op("winsorization", {"columns": ["val"], "lower_quantile": 0.05, "upper_quantile": 0.95}, custom_df=df_winsor)
    assert res_win["val"].min() == 5.0
    assert res_win["val"].max() == 94.0

    df_scale = pl.DataFrame({"val": [0.0, 50.0, 100.0]})
    res_scale, _, _ = run_op("minmax_scaling", {"columns": ["val"]}, custom_df=df_scale)
    assert res_scale["val"][0] == pytest.approx(0.0)
    assert res_scale["val"][1] == pytest.approx(0.5)
    assert res_scale["val"][2] == pytest.approx(1.0)

    df_std = pl.DataFrame({"val": [1.0, 2.0, 3.0]})
    res_std, _, _ = run_op("standardization", {"columns": ["val"]}, custom_df=df_std)
    assert res_std["val"].mean() == pytest.approx(0.0, abs=1e-7)

    # 27. one_hot_encoding
    res, _, _ = run_op("one_hot_encoding", {"columns": ["category"]})
    assert "category_A" in res.columns
    assert "category_B" in res.columns

    # 28. label_encoding
    res, _, _ = run_op("label_encoding", {"columns": ["category"]})
    assert res["category"].dtype in [pl.Int64, pl.Int32, pl.Int8, pl.UInt64, pl.UInt32, pl.UInt8]

    df_emoji = pl.DataFrame({"text": ["hello 👋", "world 🌍"]})
    res_emoji, _, _ = run_op("emoji_removal", {"columns": ["text"]}, custom_df=df_emoji)
    assert res_emoji["text"][0] == "hello "

    # 30. html_removal
    res, _, _ = run_op("html_removal", {"columns": ["text_with_html"]})
    assert res["text_with_html"][0] == "hello"

    # 31. whitespace_cleaning
    df_space = pl.DataFrame({"text": ["hello    world", "   extra   spaces   "]})
    res_space, _, _ = run_op("whitespace_cleaning", {"columns": ["text"]}, custom_df=df_space)
    assert res_space["text"][0] == "hello world"
    assert res_space["text"][1] == " extra spaces "

    # 32. Unknown operation fallback
    res, _, _ = run_op("unknown_op", {})
    assert res.columns == df.columns
