import pytest
import os
import polars as pl
from unittest.mock import MagicMock, patch
from connectors import (
    infer_extension,
    read_dataset_from_bytes,
    read_csv_from_bytes,
    _read_csv_variants,
    _read_json_dataset,
    _read_excel_dataset,
    _read_parquet_dataset
)
from identifier import _extract_json, identify_dataset_semantics

def test_infer_extension():
    assert infer_extension(None) == ".csv"
    assert infer_extension("") == ".csv"
    assert infer_extension("test.CSV") == ".csv"
    assert infer_extension("no_suffix") == ".csv"
    assert infer_extension("file.parquet") == ".parquet"


def test_read_csv_variants():
    # Happy path UTF-8
    df = _read_csv_variants(b"a,b\n1,2\n3,4")
    assert df.columns == ["a", "b"]
    assert df.height == 2

    # UTF-16 with BOM fallback
    utf16_data = "\ufeffa,b\n1,2\n3,4".encode("utf-16")
    with patch("polars.read_csv", side_effect=[Exception("utf8 fail"), pl.DataFrame({"a": [1, 3], "b": [2, 4]})]):
        df_u16 = _read_csv_variants(utf16_data)
        assert df_u16.columns == ["a", "b"]

    # cp1252/latin-1 encoding fallback
    latin1_data = "a,b\n1,mü\n3,4".encode("latin-1")
    with patch("polars.read_csv", side_effect=[Exception("utf8 fail"), pl.DataFrame({"a": [1, 3], "b": [2, 4]})]):
        df_latin = _read_csv_variants(latin1_data)
        assert df_latin.columns == ["a", "b"]

    # utf8-lossy fallback
    lossy_data = b"a,b\n1,\xff\n3,4"
    with patch("polars.read_csv", side_effect=[Exception("utf8 fail"), Exception("utf16 fail"), Exception("cp1252 fail"), pl.DataFrame({"a": [1, 3], "b": [2, 4]})]):
        df_lossy = _read_csv_variants(lossy_data)
        assert df_lossy.columns == ["a", "b"]

    # Exception path: totally invalid CSV
    with patch("polars.read_csv", side_effect=Exception("Read error")):
        with pytest.raises(ValueError, match="CSV decoding failed"):
            _read_csv_variants(b"some bytes")


def test_read_json_dataset():
    # Happy path JSON array
    df = _read_json_dataset(b'[{"a": 1}, {"a": 2}]')
    assert df.columns == ["a"]

    # UTF-8 BOM JSON
    df_bom = _read_json_dataset(b'\xef\xbb\xbf[{"a": 1}]')
    assert df_bom.columns == ["a"]

    # JSON dict with "data" key
    df_dict_data = _read_json_dataset(b'{"data": [{"a": 1, "b": 2}]}')
    assert df_dict_data.columns == ["a", "b"]

    # JSON dict without "data" key (converts to single row)
    df_dict = _read_json_dataset(b'{"a": 1, "b": 2}')
    assert df_dict.height == 1

    # NDJSON (New-line delimited)
    df_ndjson = _read_json_dataset(b'{"a": 1}\n{"a": 2}')
    assert df_ndjson.height == 2

    # Empty JSON
    with pytest.raises(ValueError, match="JSON file is empty"):
        _read_json_dataset(b"   ")

    # Invalid JSON not list or dict
    with pytest.raises(ValueError, match="JSON must decode to a list or object"):
        _read_json_dataset(b"12345")


def test_read_excel_dataset():
    # Excel requires actual Excel bytes, let's mock pd.read_excel
    import pandas as pd
    mock_df = pd.DataFrame({"a": [1, 2]})
    
    with patch("pandas.read_excel", return_value=mock_df) as mock_read:
        df = _read_excel_dataset(b"mock excel bytes")
        assert df.columns == ["a"]
        assert mock_read.call_count == 1

    # Test openpyxl fail fallback
    with patch("pandas.read_excel", side_effect=[Exception("openpyxl error"), mock_df]) as mock_read_fail:
        df = _read_excel_dataset(b"mock excel bytes")
        assert df.columns == ["a"]
        assert mock_read_fail.call_count == 2


def test_read_parquet_dataset():
    # Mock pl.read_parquet
    mock_df = pl.DataFrame({"a": [1, 2]})
    with patch("polars.read_parquet", return_value=mock_df):
        df = _read_parquet_dataset(b"mock parquet bytes")
        assert df.columns == ["a"]


def test_read_dataset_from_bytes():
    # CSV
    df_csv = read_dataset_from_bytes(b"a,b\n1,2", "data.csv")
    assert df_csv.columns == ["a", "b"]

    # TSV
    df_tsv = read_dataset_from_bytes(b"a\tb\n1\t2", "data.tsv")
    assert df_tsv.columns == ["a", "b"]

    # JSON
    df_json = read_dataset_from_bytes(b'[{"a": 1}]', "data.json")
    assert df_json.columns == ["a"]

    # Parquet
    mock_df = pl.DataFrame({"a": [1]})
    with patch("polars.read_parquet", return_value=mock_df):
        df_pq = read_dataset_from_bytes(b"parquet bytes", "data.parquet")
        assert df_pq.columns == ["a"]

    # Excel
    import pandas as pd
    mock_pandas = pd.DataFrame({"a": [1]})
    with patch("pandas.read_excel", return_value=mock_pandas):
        df_xl = read_dataset_from_bytes(b"excel bytes", "data.xlsx")
        assert df_xl.columns == ["a"]

    # Unsupported
    with pytest.raises(ValueError, match="Unsupported file type"):
        read_dataset_from_bytes(b"bytes", "data.txt")

    # read_csv_from_bytes helper
    df_helper = read_csv_from_bytes(b"a,b\n1,2")
    assert df_helper.columns == ["a", "b"]


def test_extract_json():
    # Simple JSON
    assert _extract_json('{"a": 1}') == {"a": 1}
    
    # Markdown wrap JSON
    assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}

    # Embedded JSON in text
    assert _extract_json('Here is your json: {"a": 1} hope you like it.') == {"a": 1}

    # Invalid JSON
    with pytest.raises(Exception):
        _extract_json("not json")


@patch("identifier.OpenAI")
def test_identify_dataset_semantics_openai_missing(mock_openai):
    df = pl.DataFrame({"a": [1, 2]})
    
    # Simulate OpenAI is None (not installed)
    with patch("identifier.OpenAI", None):
        res = identify_dataset_semantics(df)
        assert res["domain"] == "Unknown"
        assert "not installed" in res["error"]


@patch("identifier.OpenAI")
def test_identify_dataset_semantics_no_api_key(mock_openai_class):
    df = pl.DataFrame({"a": [1, 2]})
    
    # Simulate OPENAI_API_KEY is not configured
    with patch.dict(os.environ, {}, clear=True):
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        res = identify_dataset_semantics(df)
        assert res["domain"] == "Unknown"
        assert "not configured" in res["error"]


@patch("identifier.OpenAI")
def test_identify_dataset_semantics_success(mock_openai_class):
    # Setup OpenAI client mock
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    mock_choice = MagicMock()
    mock_choice.message.content = '```json\n{"domain": "Finance", "confidence": 95, "columns": [{"name": "a", "semantic_type": "ID", "confidence": 90}]}\n```'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    df = pl.DataFrame({"a": [1, 2]})
    
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        res = identify_dataset_semantics(df)
        assert res["domain"] == "Finance"
        assert res["confidence"] == 95
        assert len(res["columns"]) == 1
        assert res["columns"][0]["semantic_type"] == "ID"


@patch("identifier.OpenAI")
def test_identify_dataset_semantics_exception(mock_openai_class):
    mock_openai_class.side_effect = Exception("OpenAI API error")
    df = pl.DataFrame({"a": [1, 2]})
    
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        res = identify_dataset_semantics(df)
        assert res["domain"] == "Unknown"
        assert "Domain identification failed" in res["error"]
