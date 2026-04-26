"""Initial schema: sources, properties, property_raws, property_images, scrape_runs

Revision ID: 0001
Revises:
Create Date: 2026-04-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    business_type_enum = postgresql.ENUM(
        "sale", "rent", name="businesstype", create_type=False
    )
    property_type_enum = postgresql.ENUM(
        "casa", "apartamento", "terreno", "sobrado", "comercial",
        "sala", "barracao", "chacara", "sitio", "fazenda", "outro",
        name="propertytype",
        create_type=False,
    )
    property_status_enum = postgresql.ENUM(
        "active", "inactive", "removed", name="propertystatus", create_type=False
    )
    scrape_run_status_enum = postgresql.ENUM(
        "running", "success", "failed", "partial", name="scraperunstatus", create_type=False
    )

    # Create shared enum types once before creating tables that reference them.
    business_type_enum.create(op.get_bind(), checkfirst=True)
    property_type_enum.create(op.get_bind(), checkfirst=True)
    property_status_enum.create(op.get_bind(), checkfirst=True)
    scrape_run_status_enum.create(op.get_bind(), checkfirst=True)

    # sources
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False,
                   comment="Imobzi/Kenlo/Imonov/Apre.me/Union"),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    )

    # properties
    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("source_property_id", sa.String(255), nullable=False,
                   comment="ID from source portal"),
        sa.Column("source_url", sa.String(1024), nullable=False),
        sa.Column(
            "business_type",
            business_type_enum,
            nullable=False,
        ),
        sa.Column("property_type", property_type_enum, nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("condominium_fee", sa.Numeric(12, 2), nullable=True),
        sa.Column("iptu", sa.Numeric(12, 2), nullable=True),
        sa.Column("city", sa.String(100), nullable=False, server_default="Ji-Paraná"),
        sa.Column("state", sa.String(2), nullable=False, server_default="RO"),
        sa.Column("neighborhood", sa.String(255), nullable=True),
        sa.Column("address_text", sa.String(500), nullable=True),
        sa.Column("bedrooms", sa.Integer, nullable=True),
        sa.Column("suites", sa.Integer, nullable=True),
        sa.Column("bathrooms", sa.Integer, nullable=True),
        sa.Column("garage_spaces", sa.Integer, nullable=True),
        sa.Column("total_area", sa.Float, nullable=True),
        sa.Column("built_area", sa.Float, nullable=True),
        sa.Column("land_area", sa.Float, nullable=True),
        sa.Column(
            "status",
            property_status_enum,
            nullable=False,
            server_default="active",
        ),
        sa.Column("is_new", sa.Boolean(), nullable=False, server_default="true", index=True),
        sa.Column("published_at_source", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
        sa.Column("last_scraped_at", sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    )

    op.create_index("idx_property_source_ref", "properties",
                     ["source_id", "source_property_id"], unique=True)
    op.create_index("idx_property_status", "properties", ["status"])
    op.create_index("idx_property_neighborhood", "properties", ["neighborhood"])
    op.create_index("idx_property_business_type", "properties", ["business_type"])

    # property_images
    op.create_table(
        "property_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )

    # property_raws
    op.create_table(
        "property_raws",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("properties.id", ondelete="SET NULL"),
                   nullable=True, index=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("scraped_at", sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
        sa.Column("raw_json", postgresql.JSON, nullable=False),
    )

    # scrape_runs
    op.create_table(
        "scrape_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            scrape_run_status_enum,
            nullable=False,
            server_default="running",
        ),
        sa.Column("properties_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("properties_new", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("properties_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_log", postgresql.JSON, nullable=True),
    )

    # Seed initial sources
    op.execute("""
        INSERT INTO sources (id, name, base_url, platform, is_active, created_at)
        VALUES
            (gen_random_uuid(), 'Jardins Imobiliaria', 'https://www.jardinsimobiliaria.com.br', 'Imobzi', true, now()),
            (gen_random_uuid(), 'Arrimo Imoveis', 'https://arrimoimoveis.com.br', 'Imonov', true, now()),
            (gen_random_uuid(), 'Porto Real Imoveis', 'https://porto-real.com', 'Kenlo', true, now()),
            (gen_random_uuid(), 'Nova Opcao Imoveis', 'https://imobiliarianovaopcao.com.br', 'Apre.me', true, now()),
            (gen_random_uuid(), 'City Imoveis', 'https://cityimoveis.imb.br', 'Union', true, now())
    """)


def downgrade() -> None:
    op.drop_table("property_raws")
    op.drop_table("property_images")
    op.drop_table("scrape_runs")
    op.drop_table("properties")
    op.drop_table("sources")

    sa.Enum(name="scraperunstatus").drop(op.get_bind(), if_exists=True)
    sa.Enum(name="propertystatus").drop(op.get_bind(), if_exists=True)
    sa.Enum(name="propertytype").drop(op.get_bind(), if_exists=True)
    sa.Enum(name="businesstype").drop(op.get_bind(), if_exists=True)
