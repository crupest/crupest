# CRUD Technic Notes

## Overview

The ultimate CRUD scaffold finally comes.

## Database Pipeline

### Select

1. Create select `what`, where clause, order clause, `Offset` and `Limit`.
2. Check clauses' related columns are valid. Then generate sql string and param list.
3. Convert param list to `Dapper` dynamic params with proper type conversion in `IColumnTypeInfo`. Execute sql and get `dynamic`s.
4. For each column:
    1. If column not in query result is null, null will be used to call hooks.
    2. If column is `NULL`, `DbNullValue` will be used to call hooks.
    3. Otherwise run conversion in `IColumnTypeInfo`.
    4. Run hook `AfterSelect` for every column.
5. Convert `dynamic`s to `TEntity`s.

### Insert

1. Create insert clause consisting of insert items.
2. Check clauses' related columns are valid. Then generate sql string and param list.
3. For each column:
    1. If insert item exits and value is not null but the column `IsGenerated` is true, throw exception.
    2. If insert item does not exist or value is `null` for that column, use default value generator to generate value. However, `DbNullValue` always means use `NULL` for that column.
    3. Coerce null to `DbNullValue`.
    4. Run hook `BeforeInsert`.
    5. Coerce null to `DbNullValue`.
    6. Run validator.
4. Convert param list to `Dapper` dynamic params with proper type conversion in `IColumnTypeInfo`. Execute sql and return `KeyColumn` value.

### Update

1. Create update clause consisted of update items, where clause.
2. Check clauses' related columns are valid. Then generate sql string and param list.
3. For each column:
    1. If insert item does not exist, `null` will be used to call hooks. However, `DbNullValue` always means use `NULL` for that column.
    2. Run hook `BeforeInsert`. If value is null, it means do not update this column.
    3. Run validator if `value` is not null.
4. Convert param list to `Dapper` dynamic params with proper type conversion in `IColumnTypeInfo`. Execute sql and get count of affected rows.
