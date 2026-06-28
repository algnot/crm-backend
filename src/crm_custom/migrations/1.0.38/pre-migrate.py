def migrate(cr, version):
    cr.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'partner_warranty_product' AND column_name = 'image'
        """
    )
    if not cr.fetchone():
        cr.execute(
            """
            ALTER TABLE partner_warranty_product
            ADD COLUMN image VARCHAR
            """
        )
