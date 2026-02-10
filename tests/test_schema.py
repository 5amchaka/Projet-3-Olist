"""Tests de cohérence entre les modèles ORM et le DDL SQL."""

import re

from src.config import PROJECT_ROOT
from src.database.models import Base


def _parse_ddl_tables(ddl_text: str) -> dict[str, set[str]]:
    """Extraire les colonnes de chaque CREATE TABLE du DDL."""
    tables: dict[str, set[str]] = {}
    pattern = re.compile(
        r"CREATE\s+TABLE\s+(\w+)\s*\((.*?)\);",
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(ddl_text):
        table_name = match.group(1)
        body = match.group(2)
        columns: set[str] = set()
        for line in body.split("\n"):
            line = line.strip().rstrip(",")
            if not line:
                continue
            # Ignorer les contraintes
            first_token = line.split("(")[0].split()[0].upper() if line.split() else ""
            if first_token in ("FOREIGN", "CHECK", "UNIQUE", "PRIMARY", "CONSTRAINT"):
                continue
            # Le premier mot est le nom de la colonne
            col_name = line.split()[0]
            columns.add(col_name)
        tables[table_name] = columns
    return tables


class TestSchemaCoherence:
    def test_orm_tables_match_ddl_tables(self):
        """Chaque table ORM doit exister dans le DDL."""
        ddl_path = PROJECT_ROOT / "sql" / "create_star_schema.sql"
        ddl_text = ddl_path.read_text()
        ddl_tables = _parse_ddl_tables(ddl_text)

        orm_table_names = {
            mapper.local_table.name for mapper in Base.registry.mappers
        }

        for table_name in orm_table_names:
            assert table_name in ddl_tables, (
                f"Table ORM '{table_name}' absente du DDL"
            )

    def test_orm_columns_match_ddl_columns(self):
        """Les colonnes de chaque modèle ORM doivent correspondre au DDL."""
        ddl_path = PROJECT_ROOT / "sql" / "create_star_schema.sql"
        ddl_text = ddl_path.read_text()
        ddl_tables = _parse_ddl_tables(ddl_text)

        for mapper in Base.registry.mappers:
            table_name = mapper.local_table.name
            orm_columns = {col.name for col in mapper.local_table.columns}
            ddl_columns = ddl_tables.get(table_name, set())

            assert orm_columns == ddl_columns, (
                f"Table '{table_name}' — différences de colonnes :\n"
                f"  ORM seulement : {orm_columns - ddl_columns}\n"
                f"  DDL seulement : {ddl_columns - orm_columns}"
            )
