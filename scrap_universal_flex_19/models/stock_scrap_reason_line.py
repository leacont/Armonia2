# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockScrapReasonLine(models.Model):
    _name = "stock.scrap.reason.line"
    _description = "Scrap Reason Split Line"
    _order = "sequence, id"

    scrap_id = fields.Many2one(
        "stock.scrap",
        string="Scrap",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    reason_id = fields.Many2one(
        "stock.scrap.reason.tag",
        string="Reason",
        required=True,
        ondelete="restrict",
    )
    category_id = fields.Many2one(
        "scrap.category",
        string="Category",
        related="reason_id.category_id",
        store=True,
        readonly=True,
    )
    allocated_qty = fields.Float(
        string="Allocated Qty",
        digits="Product Unit of Measure",
        default=0.0,
        help="Portion of total scrap quantity assigned to this reason.",
    )
    note = fields.Char(string="Line Note")
    ratio_pct = fields.Float(
        string="% of Scrap",
        compute="_compute_ratio_pct",
        digits=(16, 2),
    )

    @api.depends("allocated_qty", "scrap_id.scrap_qty", "scrap_id.product_uom_id")
    def _compute_ratio_pct(self):
        for line in self:
            scrap = line.scrap_id
            if not scrap.product_uom_id or scrap.product_uom_id.is_zero(scrap.scrap_qty):
                line.ratio_pct = 0.0
            else:
                line.ratio_pct = (line.allocated_qty / scrap.scrap_qty) * 100.0

    def write(self, vals):
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        return super().create(vals_list)

    def unlink(self):
        return super().unlink()
