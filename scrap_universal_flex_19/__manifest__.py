# -*- coding: utf-8 -*-
{
    "name": "Multi Scrap & Unscrap Management",
    "version": "18.0.3.0.0",
    "category": "Inventory/Inventory",
    "summary": "Advanced scrap and unscrap management with multi-reason split, categories, audit trail, and controlled reversals.",
    "description": """
Multi Scrap & Unscrap Management (Odoo 18)
==========================================

Professional scrap operations for manufacturing and inventory teams.

Key features
------------
- Scrap Categories and Scrap Reasons configuration under Inventory settings.
- Each scrap reason is linked to one scrap category.
- Multi-reason scrap split with quantity validation.
- Single-reason and multi-reason scrap flows in the same screen.
- Bulk loading of reasons from selected categories.
- Unified Reason and Scrap Category visibility in the scrap list.
- Unscrap wizard with mandatory Reason and complete audit history.
- Full/partial unscrap control with safe validation rules.
- Unscrap records generated with dedicated reference format.
- Extra operational fields: Reference Code, Root Cause, Corrective Action.
- Projected stock balance (before/after scrap).

Business value
--------------
- Improve traceability and root-cause analysis.
- Standardize scrap governance across teams.
- Reduce manual errors in scrap reversal workflows.
    """,
    "author": "Armonia",
    "website": "",
    "license": "OPL-1",
    "price": 19.9,
    "currency": "USD",
    "depends": ["stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/scrap_config_views.xml",
        "views/stock_scrap_views.xml",
        "wizards/stock_scrap_unscrap_wizard_views.xml",
    ],
    "images": [
        "static/description/banner.png",
        "static/description/icon.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
