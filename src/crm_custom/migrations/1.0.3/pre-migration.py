def migrate(cr, version):
    old_model = "crm.user.point.redeem"
    new_model = "crm.partner.point.redeem"
    old_table = "crm_user_point_redeem"
    new_table = "crm_partner_point_redeem"

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

    if old_regclass or new_regclass:
        old_constraint = f"{old_table}_point_redeem_code_uniq"
        new_constraint = f"{new_table}_point_redeem_code_uniq"
        cr.execute(
            """
            SELECT 1
              FROM pg_constraint
             WHERE conname = %s
               AND conrelid = %s::regclass
            """,
            (old_constraint, new_table),
        )
        has_old_constraint = cr.fetchone()
        cr.execute(
            """
            SELECT 1
              FROM pg_constraint
             WHERE conname = %s
               AND conrelid = %s::regclass
            """,
            (new_constraint, new_table),
        )
        has_new_constraint = cr.fetchone()
        if has_old_constraint and not has_new_constraint:
            cr.execute(
                f'ALTER TABLE "{new_table}" '
                f'RENAME CONSTRAINT "{old_constraint}" TO "{new_constraint}"'
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
        UPDATE ir_model_fields
           SET model = %s
         WHERE model = %s
        """,
        (new_model, old_model),
    )
    cr.execute(
        """
        UPDATE ir_model_data
           SET name = replace(name, 'field_crm_user_point_redeem__', 'field_crm_partner_point_redeem__')
         WHERE module = 'crm_custom'
           AND name LIKE 'field_crm_user_point_redeem__%%'
        """
    )
    cr.execute(
        """
        UPDATE ir_model_data
           SET name = 'model_crm_partner_point_redeem'
         WHERE module = 'crm_custom'
           AND name = 'model_crm_user_point_redeem'
        """
    )
    cr.execute(
        """
        UPDATE ir_model_data
           SET name = 'access_crm_partner_point_redeem'
         WHERE module = 'crm_custom'
           AND name = 'access_crm_user_point_redeem'
        """
    )
