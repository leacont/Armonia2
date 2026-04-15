# -*- coding: utf-8 -*-
# Odoo 18 — technical name: bom_multinivel_18. Install from Apps (requires Manufacturing and Sales).
# Do not install together with bom_multinivel (19) on the same database.
{
    "name": "Multi-Level BoM Explorer",
    "version": "18.0.2.0.0",
    "category": "Manufacturing/Manufacturing",
    "summary": "Automatic multilevel MO explosion, phantom kit expansion, project numbering, and traceable child MOs—built for real BoM depth.",
    "description": """
Multi-Level BoM Explorer (Odoo 18.0)
====================================

**Manufacturing orders that match how your product is actually built.**

When a finished product has sub-assemblies—and those sub-assemblies have their own BoMs—creating every MO by hand is slow and error-prone.
This module **confirms the parent MO and automatically creates and confirms child MOs** down the BoM tree, using Odoo’s standard BoM lookup
(company, operation type, active BoMs) and respecting variant line skips.

**Highlights**
------------
* **Recursive propagation on MO confirm** — for each BoM line, if the component has a manufacturing BoM, a child MO is created, confirmed, and the process continues.
* **Phantom (kit) BoMs** — exploded without generating a kit MO; components are processed at the right quantities.
* **Subcontracting BoMs** — intentionally skipped to avoid conflicting subcontract flows.
* **Safety** — maximum depth (25 levels) with clear logging when the cap is hit.
* **Project number** — automatic sequence (`project.number`) plus inheritance on child MOs tied through `origin`.
* **Operational continuity** — router/job/sales-order related fields on the parent are copied to generated children when those fields exist on your database.

**Dependencies:** Manufacturing (`mrp`), Sales (`sale`).

**Note:** If another module also auto-creates child MOs on confirm, you may need to align processes to prevent duplicate logic.

**Odoo 19 edition:** install the module ``bom_multinivel`` on Odoo 19 servers only.

**Support:** le.contino@gmail.com — **Armonia**
    """,
    "author": "Armonia",
    "website": "",
    "license": "OPL-1",
    "price": 29.9,
    "currency": "USD",
    "auto_install": False,
    "application": True,
    "sequence": 20,
    "depends": ["mrp", "sale"],
    "images": [
        "static/description/banner.png",
        "static/description/icon.png",
    ],
    "data": [
        "data/project_number_sequence.xml",
        "views/mrp_production_views.xml",
    ],
    "installable": True,
}
