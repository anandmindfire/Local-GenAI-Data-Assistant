"""Database schema inspector and metadata extractor for NL2SQL."""

import logging

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.constants import ALLOWED_BUSINESS_TABLES
from app.infrastructure.database.connection import get_engine

logger = logging.getLogger(__name__)


class DatabaseSchemaInspector:
    """Discovers and formats relational schema information for SQL generation prompts."""

    def __init__(self, engine: AsyncEngine | None = None) -> None:
        self.engine = engine or get_engine()
        self._cached_schema: str | None = None

    async def get_schema_representation(self, refresh: bool = False) -> str:
        """Inspect and return schema representation for whitelisted tables."""
        if self._cached_schema and not refresh:
            return self._cached_schema

        try:
            schema_text = await self._inspect_tables()
            self._cached_schema = schema_text
            return schema_text
        except Exception as e:
            logger.warning(
                f"Dynamic schema reflection failed ({e}). Using declarative fallback schema."
            )
            fallback = self.get_declarative_schema()
            self._cached_schema = fallback
            return fallback

    async def _inspect_tables(self) -> str:
        """Run synchronous SQLAlchemy inspection on engine connection."""

        def _inspect(connection):
            inspector = inspect(connection)
            table_schemas = []

            for table_name in sorted(ALLOWED_BUSINESS_TABLES):
                if not inspector.has_table(table_name):
                    continue

                columns = inspector.get_columns(table_name)
                pk_constraint = inspector.get_pk_constraint(table_name)
                pks = set(pk_constraint.get("constrained_columns", []))
                fks = inspector.get_foreign_keys(table_name)

                col_defs = []
                for col in columns:
                    name = col["name"]
                    type_str = str(col["type"])
                    nullable = "" if col.get("nullable", True) else " NOT NULL"
                    pk_marker = " PRIMARY KEY" if name in pks else ""
                    col_defs.append(f"  {name} {type_str}{pk_marker}{nullable}")

                fk_defs = []
                for fk in fks:
                    cols = ", ".join(fk["constrained_columns"])
                    ref_table = fk["referred_table"]
                    ref_cols = ", ".join(fk["referred_columns"])
                    fk_defs.append(f"  FOREIGN KEY ({cols}) REFERENCES {ref_table}({ref_cols})")

                table_body = ",\n".join(col_defs + fk_defs)
                table_schemas.append(f"CREATE TABLE {table_name} (\n{table_body}\n);")

            return "\n\n".join(table_schemas)

        async with self.engine.connect() as conn:
            return await conn.run_sync(_inspect)

    @staticmethod
    def get_declarative_schema() -> str:
        """Provide explicit declarative DDL representation of allowed business tables."""
        return """CREATE TABLE customers (
  customer_id INTEGER PRIMARY KEY,
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  email VARCHAR(255) NOT NULL,
  phone VARCHAR(50),
  city VARCHAR(100) NOT NULL,
  country VARCHAR(100) NOT NULL
);

CREATE TABLE products (
  product_id INTEGER PRIMARY KEY,
  sku VARCHAR(50) NOT NULL,
  name VARCHAR(255) NOT NULL,
  category VARCHAR(100) NOT NULL,
  price NUMERIC(10, 2) NOT NULL,
  stock_quantity INTEGER NOT NULL,
  description TEXT
);

CREATE TABLE orders (
  order_id INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
  order_date TIMESTAMP WITH TIME ZONE NOT NULL,
  status VARCHAR(50) NOT NULL, -- 'completed', 'cancelled', 'processing', 'refunded'
  total_amount NUMERIC(12, 2) NOT NULL
);

CREATE TABLE order_items (
  item_id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL REFERENCES orders(order_id),
  product_id INTEGER NOT NULL REFERENCES products(product_id),
  quantity INTEGER NOT NULL,
  unit_price NUMERIC(10, 2) NOT NULL,
  subtotal NUMERIC(12, 2) NOT NULL
);

CREATE TABLE refunds (
  refund_id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL REFERENCES orders(order_id),
  refund_amount NUMERIC(12, 2) NOT NULL,
  refund_date TIMESTAMP WITH TIME ZONE NOT NULL,
  reason VARCHAR(255) NOT NULL,
  status VARCHAR(50) NOT NULL -- 'processed', 'pending', 'rejected'
);"""
