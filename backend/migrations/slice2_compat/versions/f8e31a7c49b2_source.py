"""Historical slice2 entry point, NOT an empty-database bootstrap."""
revision = 'f8e31a7c49b2'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    raise RuntimeError('Restore the supported slice2 backup; this route cannot bootstrap or stamp a database.')


def downgrade():
    raise RuntimeError('Forward-only history preservation route.')
