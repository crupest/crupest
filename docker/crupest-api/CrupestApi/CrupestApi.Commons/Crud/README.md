# CRUD Technic Notes

## Database Pipeline

### Select

1. Create select `what`, where clause, order clause, `Offset` and `Limit`.
2. Check clauses' related columns are valid. Then generate sql string and param list.
3. Convert param list to `Dapper` dynamic params. Execute sql and get `dynamic`s.
4. Run hook `AfterSelect` for every column.
5. Convert `dynamic`s to `TEntity`s.

TODO: Continue here.

### Insert

1. Create insert clause consisting of insert items.
2. Check clauses' related columns are valid. Then generate sql string and param list.
3. Run hook `BeforeInsert` for every column.
4. Convert param list to `Dapper` dynamic params. Execute sql and return `KeyColumn` value.

### Update

1. Create update clause consisting of update items, where clause.
2. Check clauses' related columns are valid. Then generate sql string and param list.
3. Run hook `BeforeUpdate` for every column.
4. Convert param list to `Dapper` dynamic params. Execute sql and get count of affected rows.
