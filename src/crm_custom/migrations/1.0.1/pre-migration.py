def migrate(cr, version):
    old_model = "crm.user.point.currency"
    new_model = "crm.partner.currency"
    old_table = "crm_user_point_currency"
    new_table = "crm_partner_currency"

    cr.execute(
        """
        SELECT to_regclass(%s), to_regclass(%s)
        """,
        (old_table, new_table),
    )
    old_regclass, new_regclass = cr.fetchone()

    if old_regclass and not new_regclass:
        cr.execute(f'ALTER TABLE "{old_table}" RENAME TO "{new_table}"')
    elif old_regclass and new_regclass:
        cr.execute(f'SELECT COUNT(*) FROM "{new_table}"')
        new_count = cr.fetchone()[0]
        if not new_count:
            cr.execute(f'DROP TABLE "{new_table}"')
            cr.execute(f'ALTER TABLE "{old_table}" RENAME TO "{new_table}"')
        else:
            cr.execute(f'SELECT COUNT(*) FROM "{old_table}"')
            old_count = cr.fetchone()[0]
            if old_count:
                raise RuntimeError(
                    f"Both {old_table} and {new_table} contain data. "
                    "Merge them manually before upgrading crm_custom."
                )

    cr.execute(
        """
        UPDATE ir_model
           SET model = %s
         WHERE model = %s
        """,
        (new_model, old_model),
    )
    cr.execute(
        """
        UPDATE ir_model_fields
           SET relation = %s
         WHERE relation = %s
        """,
        (new_model, old_model),
    )
    cr.execute(
        """
        UPDATE ir_model_data
           SET name = 'model_crm_partner_currency'
         WHERE module = 'crm_custom'
           AND name = 'model_crm_user_point_currency'
        """
    )
    cr.execute(
        """
        UPDATE ir_model_data
           SET name = 'access_crm_partner_currency'
         WHERE module = 'crm_custom'
           AND name = 'access_crm_user_point_currency'
        """
    )
