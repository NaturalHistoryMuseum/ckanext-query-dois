"""
Set old query version.

Revision ID: a74242a670e0
Revises:
Create Date: 2023-06-09 12:20:05.632095
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

# revision identifiers, used by Alembic.
revision = 'a74242a670e0'
down_revision = None
branch_labels = None
depends_on = None

Base = declarative_base()


class QueryDOI(Base):
    __tablename__ = 'query_doi'
    id = sa.Column(sa.UnicodeText, primary_key=True)
    query_version = sa.Column(sa.UnicodeText, nullable=True)


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    for query_doi in session.query(QueryDOI).filter(QueryDOI.query_version.is_(None)):
        query_doi.query_version = 'v0'

    session.commit()


def downgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    for query_doi in session.query(QueryDOI).filter(QueryDOI.query_version == 'v0'):
        query_doi.query_version = None

    session.commit()
