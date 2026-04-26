"""Add Sadeq, Nogueira, Habitare, Achou Imoveis sources

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-26

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO sources (id, name, base_url, platform, is_active, created_at)
        VALUES
            (gen_random_uuid(), 'Sadeq Imoveis', 'https://sadeqimoveis.com.br', 'Proprio', true, now()),
            (gen_random_uuid(), 'Imobiliaria Nogueira', 'https://www.imobiliarianogueira.com.br', 'Union', true, now()),
            (gen_random_uuid(), 'Habitare Ji-Parana', 'https://www.habitarejipa.com.br', 'Proprio', true, now()),
            (gen_random_uuid(), 'Achou Imoveis Ji-Parana', 'https://www.achouimoveisjiparana.com.br', 'Proprio', true, now())
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM sources WHERE name IN (
            'Sadeq Imoveis',
            'Imobiliaria Nogueira',
            'Habitare Ji-Parana',
            'Achou Imoveis Ji-Parana'
        )
    """)
