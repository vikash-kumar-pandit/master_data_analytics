# Stateless Data Platform - Error Handling Analysis Report

**Generated**: May 2, 2026
**Analysis Scope**: backend/main.py, analytics_engine.py, pdf_generator.py, report_generator.py, worker.py + frontend components

---

## EXECUTIVE SUMMARY

### Critical Issues Found: 12
- **CRITICAL (500 error risk)**: 4 issues
- **HIGH (data loss/crashes)**: 2 issues  
- **MEDIUM (validation gaps)**: 4 issues
- **LOW (user experience)**: 2 issues

### Most Likely Cause of PDF Download 500 Error
**pdf_generator.py** and **report_generator.py** have zero input validation and error handling. When the `generate_structured_report_pdf()` or `generate_structured_report_pptx()` functions receive malformed data, they crash with no fallback.

---

## CRITICAL ISSUES (Causes 500 Errors)

### Issue #1: PDF/PPTX Generation Has No Error Handling
**File**: [backend/pdf_generator.py](backend/pdf_generator.py)
**Lines**: 11-145 (all 4 functions)
**Severity**: CRITICAL
**Impact**: PDF downloads fail with 500 error

**Problems**:
- No validation that dataframe has rows/columns
- Empty dataframe crashes `pdf.iter_rows()`
- Column width can be calculated as 0
- PDF encoding can fail silently on non-latin1 characters
- No error handling for FPDF library failures

**Affected Functions**:
1. `create_pdf_in_memory()` - lines 11-22
2. `generate_pdf_in_memory()` - lines 26-60
3. `generate_structured_report_pdf()` - lines 65-95
4. `generate_structured_report_pptx()` - lines 100-145

**Example Failure**:
```python
# Current code crashes:
sample_df = dataframe.head(10)
if sample_df.columns:  # True even if dataframe is empty!
    for row in sample_df.iter_rows():  # CRASHES: no rows!
        for item in row:
```

**Fix**: Add try-catch, validate dataframe before operations, limit content size

---

### Issue #2: Report Generator Same Issues
**File**: [backend/report_generator.py](backend/report_generator.py)
**Lines**: 65-145 (all 3 functions)
**Severity**: CRITICAL
**Impact**: Report download fails with 500 error

**Problems**:
- No validation of `section.get("rows")` - can be None
- Row dict might be missing "label" or "value" keys
- No error handling for presentation.save() failures
- No size limits on content

**Affected Functions**:
1. `generate_structured_report_pdf()` - lines 65-95
2. `generate_structured_report_pptx()` - lines 100-145

**Example Failure**:
```python
# Current code crashes:
for section in sections:
    rows = section.get("rows") or []
    for row in rows:
        label = str(row.get("label") or "")  # If row is missing keys
        value = str(row.get("value") or "")  # KeyError possible
```

**Fix**: Validate section/row structure, add try-catch for each operation

---

### Issue #3: /api/analytics/report Endpoint No Validation
**File**: [backend/main.py](backend/main.py)
**Lines**: 423-456
**Severity**: CRITICAL  
**Impact**: PDF/PPTX download fails

**Problems**:
- No validation that `payload.sections` is properly formatted
- No check for empty sections list
- No validation that title/subtitle are strings
- Passes malformed data directly to generator functions

**Current Code**:
```python
@app.post("/api/analytics/report")
async def analytics_report_pdf(
    payload: StructuredReportRequest,
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        output_format = (payload.output_format or "pdf").strip().lower()
        if output_format == "pptx":
            file_bytes = generate_structured_report_pptx(  # No validation!
                title=payload.title,
                subtitle=payload.subtitle,
                sections=payload.sections,
            )
```

**Fix**: Validate all fields before calling generator functions

---

### Issue #4: /download Endpoint Missing Validations
**File**: [backend/main.py](backend/main.py)
**Lines**: 612-660
**Severity**: CRITICAL
**Impact**: Download fails with 500 error

**Problems**:
- No validation that `rows` is proper format for `pl.from_dicts()`
- `target_column` not checked if exists in dataframe
- `generate_pdf_in_memory()` called without error handling
- CSV/JSON generation not wrapped in try-catch
- Zip file operations can fail silently

**Current Code**:
```python
dataframe = pl.from_dicts(rows)  # Can crash if rows format invalid!
# ...
automl_summary = run_automl_stateless(dataframe, target_column)  # No check if column exists
# ...
zip_file.writestr("analysis_report.pdf", generate_pdf_in_memory(dataframe, report_summary))  # No error handling
```

**Fix**: Validate rows format, check column exists, wrap operations in try-catch

---

## HIGH PRIORITY ISSUES (Data Loss/Crashes)

### Issue #5: Division by Zero in analytics_engine.py
**File**: [backend/analytics_engine.py](backend/analytics_engine.py)
**Lines**: 165, 460 (in numeric_delta_summary calculation)
**Severity**: HIGH
**Impact**: Infinite values in metrics, potential crash

**Problems**:
- `pct_change` calculation does division before checking denominator
- Checks `if before_sum` AFTER division happens
- Returns `inf` instead of None for zero division

**Current Code**:
```python
"pct_change": round(((after_sum - before_sum) / before_sum) * 100, 2) if before_sum else None,
# WRONG: Division happens first, then if check!
```

**Fixed Code**:
```python
"pct_change": round(((after_sum - before_sum) / before_sum) * 100, 2) if before_sum != 0 else None,
# RIGHT: Check != 0 before division
```

**Occurs in**: 
- `analyze_question()` - line 165
- `compare_versions()` - line 460

---

### Issue #6: Worker Task No Error Handling
**File**: [backend/worker.py](backend/worker.py)
**Lines**: 17, 40
**Severity**: HIGH
**Impact**: Celery tasks crash without recovery

**Problems**:
- `async_clean_data()`: No validation of base64 string before decode
- `async_run_automl()`: No check if target_column exists in dataframe
- No error state updates in Celery
- base64.b64decode() can crash task

**Current Code**:
```python
@celery_app.task(bind=True)
def async_clean_data(self, file_base64_string: str) -> dict:
    self.update_state(state="PROGRESS", meta={"status": "Loading CSV into memory...", "progress": 20})
    
    file_bytes = base64.b64decode(file_base64_string)  # Can crash!
    # No try-catch
```

**Fix**: Add try-catch, validate inputs, update error state in Celery

---

## MEDIUM PRIORITY ISSUES (Validation Gaps)

### Issue #7: No File Size Limit on Upload
**File**: [backend/main.py](backend/main.py)
**Line**: 250-280
**Severity**: MEDIUM
**Impact**: Large files can cause memory issues, DOS attack vector

**Problems**:
- No maximum file size check
- No file type validation
- Can accept any size file

**Fix**: Add `MAX_FILE_SIZE = 100 * 1024 * 1024` check

---

### Issue #8: Row Validation Missing
**File**: [backend/main.py](backend/main.py)
**Line**: 365
**Severity**: MEDIUM
**Impact**: Invalid data causes 500 error

**Problems**:
- No validation that `rows` is list
- No check that rows aren't empty
- `previous_rows` not validated
- No length limit (could accept 1M+ rows)

**Fix**: Add type checking, length limits, structure validation

---

### Issue #9: Analytics Engine Functions Not Defensive
**File**: [backend/analytics_engine.py](backend/analytics_engine.py)
**Lines**: 73+, 92+, 150+
**Severity**: MEDIUM
**Impact**: Invalid data crashes analysis

**Problems**:
- `_numeric_columns()` called on empty dataframe
- `_cast_numeric()` assumes column exists
- `_forecast_from_points()` crashes if points < 2
- No empty dataframe checks

**Fix**: Add defensive checks before operations

---

### Issue #10: ML Engine Error Handling Incomplete
**File**: [backend/ml_engine.py](backend/ml_engine.py)
**Line**: 8+
**Severity**: MEDIUM
**Impact**: Cryptic PyCaret errors shown to user

**Problems**:
- ImportError caught but PyCaret failures not handled
- `setup()` can fail with cryptic error messages
- `pull()` can return None without error
- User sees raw PyCaret exceptions

**Fix**: Catch PyCaret exceptions, provide user-friendly messages

---

## FRONTEND ISSUES

### Issue #11: SearchAndExport Component - Generic Error Handling
**File**: [frontend/src/components/SearchAndExport.jsx](frontend/src/components/SearchAndExport.jsx)
**Line**: 42+
**Severity**: LOW
**Impact**: Poor user experience

**Problems**:
- Error shown in alert, blocks UI
- Error disappears after dismiss
- No persistent error logging
- No retry mechanism

**Fix**: Use persistent error state, provide retry option

---

### Issue #12: ScheduleExportModal - Weak Input Validation
**File**: [frontend/src/components/ScheduleExportModal.jsx](frontend/src/components/ScheduleExportModal.jsx)
**Lines**: 37, 60
**Severity**: LOW
**Impact**: Invalid schedules created

**Problems**:
- Email validation only checks for "@" (accepts "a@b")
- Cron expression not validated
- No regex pattern checks
- Server-side validation may also be weak

**Fix**: Add email regex validation, add cron expression validator

---

## ISSUE IMPACT TABLE

| Issue | File | Line | Type | 500 Error? | Data Loss? | User Impact |
|-------|------|------|------|-----------|-----------|-------------|
| PDF gen no validation | pdf_generator.py | 11-145 | CRITICAL | YES | YES | PDF download fails |
| Report gen no validation | report_generator.py | 65-145 | CRITICAL | YES | YES | Report download fails |
| Report endpoint no validation | main.py | 423 | CRITICAL | YES | NO | Report download fails |
| Download endpoint no validation | main.py | 612 | CRITICAL | YES | YES | Download zip fails |
| Division by zero | analytics_engine.py | 165, 460 | HIGH | NO | NO | Wrong metrics in reports |
| Worker tasks no error handling | worker.py | 17, 40 | HIGH | NO | YES | Celery tasks crash |
| No file size limit | main.py | 250 | MEDIUM | NO | NO | Memory issues possible |
| Row validation missing | main.py | 365 | MEDIUM | YES | NO | Analysis crashes |
| Analytics not defensive | analytics_engine.py | 73+ | MEDIUM | YES | NO | Analysis crashes |
| ML engine error handling | ml_engine.py | 8+ | MEDIUM | YES | NO | Confusing errors |
| Poor error UX | SearchAndExport.jsx | 42 | LOW | NO | NO | Bad UX |
| Weak input validation | ScheduleExportModal.jsx | 37, 60 | LOW | NO | NO | Bad schedules created |

---

## RECOMMENDED FIX PRIORITY

### Phase 1 (IMMEDIATE - Fixes 500 Errors)
1. **pdf_generator.py** - Add input validation and error handling (2-3 hours)
2. **report_generator.py** - Add input validation and error handling (2-3 hours)
3. **main.py /api/analytics/report** - Add payload validation (1 hour)
4. **main.py /download** - Add data validation and error handling (1-2 hours)

### Phase 2 (URGENT - Prevents Crashes)
5. **analytics_engine.py** - Fix division by zero (30 mins)
6. **analytics_engine.py** - Add defensive checks (1 hour)
7. **worker.py** - Add error handling for base64 and target_column (1 hour)

### Phase 3 (IMPORTANT - Improves Reliability)
8. **main.py** - Add file size limit to upload (30 mins)
9. **main.py** - Add row validation to all analytics endpoints (2 hours)
10. **ml_engine.py** - Add PyCaret error handling (1 hour)

### Phase 4 (NICE TO HAVE - Better UX)
11. **Frontend** - Improve error messages and validation (2 hours)
12. **Add logging** - Comprehensive error logging (2 hours)

---

## TESTING RECOMMENDATIONS

### Unit Tests Needed
- `test_pdf_generator_empty_dataframe()` - Verify PDF gen handles empty data
- `test_report_generator_invalid_sections()` - Verify section validation
- `test_analytics_zero_division()` - Verify pct_change calculation
- `test_file_upload_size_limit()` - Verify file size rejected

### Integration Tests Needed
- `/api/analytics/report` with invalid sections
- `/download` with mismatched target_column
- Celery tasks with invalid base64
- Backend → Frontend error message flow

### Manual Tests
- Try uploading 1GB file
- Try report with 10,000 sections
- Try with corrupted CSV
- Check error messages in browser console

---

## CODE REVIEW CHECKLIST

Before deployment, ensure:
- [ ] All API endpoints validate input types
- [ ] All file operations wrapped in try-catch
- [ ] PDF/PPTX generation has fallback paths
- [ ] No division by zero possible
- [ ] File size limits enforced
- [ ] Error messages logged for debugging
- [ ] Frontend shows persistent errors
- [ ] Timeout handling present for long operations
- [ ] null/None checks before accessing dict keys
- [ ] Empty list/dataframe checks before iteration

