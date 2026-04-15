# -*- coding: utf-8 -*-

from odoo import fields, models


class ScrapCategory(models.Model):
    _name = "scrap.category"
    _description = "Scrap Category"
    _order = "name, id"

    name = fields.Char(required=True, translate=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)

    _sql_constraints = [
        (
            "scrap_category_name_company_uniq",
            "unique(name, company_id)",
            "Category name must be unique per company.",
        ),
    ]
