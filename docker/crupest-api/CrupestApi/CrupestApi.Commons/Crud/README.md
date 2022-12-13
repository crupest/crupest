# CRUD Technic Notes

## Overview

The ultimate CRUD scaffold finally comes.

## Database Pipeline

### Select

1. Create select `what`, where clause, order clause, `Offset` and `Limit`.
2. Check clauses' related columns are valid.
3. Generate sql string and param list.
4. Convert param list to `Dapper` dynamic params with proper type conversion in `IColumnTypeInfo`.
5. Execute sql and get `dynamic`s.
6. (Optional) Convert `dynamic`s to `TEntity`s.

### Insert

1. Create insert clause.
2. Check clauses' related columns are valid.
3. Create a real empty insert clause.
4. For each column:
    1. If insert item exists and value is not null but the column `IsGenerated` is true, throw exception.
    2. If insert item does not exist or value is `null`, use default value generator to generate value. However, `DbNullValue` always means use `NULL` for that column.
    3. If value is `null` and the column `IsAutoIncrement` is true, skip to next column.
    4. Coerce null to `DbNullValue`.
    5. Run validator to validate the value.
    6. If value is `DbNullValue`, `IsNotNull` is true, throw exception.
    7. Add column and value to real insert clause.
5. Generate sql string and param list.
6. Convert param list to `Dapper` dynamic params with proper type conversion in `IColumnTypeInfo`.
7. Execute sql and return `KeyColumn` value.

### Update

1. Create update clause, where clause.
2. Check clauses' related columns are valid. Then generate sql string and param list.
3. Create a real empty update clause.
4. For each column:
    1. If update item exists and value is not null but the column `IsNoUpdate` is true, throw exception.
    2. Invoke validator to validate the value.
    3. If `IsNotNull` is true and value is `DbNullValue`, throw exception.
    4. Add column and value to real update clause.
5. Generate sql string and param list.
6. Convert param list to `Dapper` dynamic params with proper type conversion in `IColumnTypeInfo`.
7. Execute sql and return count of affected rows.
