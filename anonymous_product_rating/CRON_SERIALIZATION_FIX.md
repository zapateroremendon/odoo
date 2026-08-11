# Cron Serialization Recovery Fix - 2026-02-10 08:35

## Problem Identified

The `cron_serialization_recovery` was generating 50+ errors per execution:
```
ERROR: Error invalidating rating cache: Cannot add to recompute no-store or no-computed field
```

## Root Cause

The `_invalidate_rating_cache()` method was attempting to invalidate **non-stored computed fields** (`store=False`):
- `total_rating_count` (store=False)
- `total_rating_avg` (store=False)

Odoo's `env.add_to_compute()` only works with **stored fields** (`store=True`). Non-stored fields are computed on-the-fly and don't need cache invalidation.

## Solution Implemented

### Option 1: Fixed `_invalidate_rating_cache()` Method
**File:** `models/product_template.py`

**Before:**
```python
def _invalidate_rating_cache(self):
    try:
        self.env.add_to_compute(self._fields['rating_count'], self)
        self.env.add_to_compute(self._fields['rating_avg'], self)
        self.env.add_to_compute(self._fields['total_rating_count'], self)  # ❌ ERROR
        self.env.add_to_compute(self._fields['total_rating_avg'], self)    # ❌ ERROR
```

**After:**
```python
def _invalidate_rating_cache(self):
    try:
        # Only invalidate STORED computed fields (store=True)
        self.env.add_to_compute(self._fields['rating_count'], self)
        self.env.add_to_compute(self._fields['rating_avg'], self)
        # Note: total_rating_count and total_rating_avg have store=False
```

### Option 2: Simplified `force_rating_recomputation()` Method

**Before:**
```python
def force_rating_recomputation(self):
    try:
        self._invalidate_rating_cache()  # Unnecessary step
        self._compute_rating_stats()
        self._compute_total_rating_stats()
```

**After:**
```python
def force_rating_recomputation(self):
    try:
        # Directly call compute methods - more reliable
        self._compute_rating_stats()
        self._compute_total_rating_stats()
```

## Verification Results

### Test Execution
```
Products with ratings: 37
Products processed: 50
Status: SUCCESS - No cache invalidation errors!
```

### Log Output (Before Fix)
```
ERROR: Error invalidating rating cache: Cannot add to recompute no-store or no-computed field
(repeated 50+ times)
```

### Log Output (After Fix)
```
INFO: Product template refresh completed for 13 products
INFO: Serialization recovery completed for 50 products
✓ No errors
```

## Benefits

✅ **Clean logs** - No more cache invalidation errors  
✅ **Correct logic** - Only invalidates stored fields  
✅ **Simpler code** - Direct computation instead of invalidation  
✅ **Same functionality** - All features work as before  
✅ **Better performance** - Removes unnecessary invalidation step  

## Field Storage Configuration

| Field | Store | Needs Invalidation |
|-------|-------|-------------------|
| `rating_count` | True | ✓ Yes |
| `rating_avg` | True | ✓ Yes |
| `total_rating_count` | False | ✗ No (computed on-the-fly) |
| `total_rating_avg` | False | ✗ No (computed on-the-fly) |
| `anonymous_rating_count` | True | ✓ Yes |
| `anonymous_rating_avg` | True | ✓ Yes |

## Conclusion

The fix resolves the design flaw where the code attempted to invalidate non-stored computed fields. The cron now runs cleanly without errors while maintaining all recovery functionality.
