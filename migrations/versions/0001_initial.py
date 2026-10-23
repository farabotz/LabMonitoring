"""Schema prototipe awal, termasuk dua partial unique index sesi terbuka."""
from alembic import op
from services.api.models import Base

revision = "0001"
down_revision = None


def upgrade():
    Base.metadata.create_all(op.get_bind())


def downgrade():
    raise RuntimeError("Downgrade destruktif dinonaktifkan. Pulihkan backup ke database baru.")
