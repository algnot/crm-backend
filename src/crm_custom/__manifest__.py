{
    "name": "CRM Custom Module",
    "version": "1.0.3",
    "summary": "CRM Custom Module",
    "author": "tk dev",
    "depends": ["base", "mail"],
    "external_dependencies": {
        "python": ["Pillow", "python-barcode"],
    },
    "assets": {
        "web.assets_backend": [],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/partner/table_view.xml",
        "views/partner/form_view.xml",
        "views/partner/coupons_view.xml",
        "views/partner/action_view.xml",
        "views/user/table_view.xml",
        "views/user/form_view.xml",
        "views/user/action_view.xml",
        "views/user/point_redeem_view.xml",
        "views/user/point_redeem_generate_wizard_view.xml",
        "views/system/otp_table_view.xml",
        "views/system/otp_form_view.xml",
        "views/system/otp_action_view.xml",
        "views/menu_view.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False
}
