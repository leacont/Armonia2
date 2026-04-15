# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class StockScrapUnscrapWizard(models.TransientModel):
    _name = "stock.scrap.unscrap.wizard"
    _description = "Unscrap Wizard"

    scrap_id = fields.Many2one("stock.scrap", string="Scrap", required=True)
    product_id = fields.Many2one(related="scrap_id.product_id", string="Product", readonly=True)
    product_uom_id = fields.Many2one(related="scrap_id.product_uom_id", string="UoM", readonly=True)
    available_qty = fields.Float(
        string="Available Qty",
        compute="_compute_available_qty",
        digits="Product Unit of Measure",
        readonly=True,
    )
    qty = fields.Float(string="Unscrap Qty", required=True, digits="Product Unit of Measure")
    to_location_id = fields.Many2one(
        "stock.location",
        string="Destination Location",
        required=True,
        domain="[('usage', '=', 'internal')]",
    )
    reason = fields.Char(string="Reason", required=True)
    note = fields.Char(string="Note")

    @api.depends("scrap_id")
    def _compute_available_qty(self):
        for wizard in self:
            wizard.available_qty = wizard.scrap_id.unscrap_qty_available

    @api.onchange("scrap_id")
    def _onchange_scrap_id(self):
        for wizard in self:
            if wizard.scrap_id:
                wizard.qty = wizard.scrap_id.unscrap_qty_available
                wizard.to_location_id = wizard.scrap_id.location_id

    def _check_qty(self):
        self.ensure_one()
        if self.qty <= 0:
            raise ValidationError(_("Unscrap quantity must be greater than zero."))
        if not self.product_uom_id:
            raise ValidationError(_("Missing UoM on scrap record."))
        if self.product_uom_id.compare(self.qty, self.available_qty) > 0:
            raise ValidationError(
                _(
                    "Unscrap quantity (%(qty)s) cannot exceed remaining available (%(available)s).",
                    qty=self.qty,
                    available=self.available_qty,
                )
            )

    def action_confirm_unscrap(self):
        self.ensure_one()
        scrap = self.scrap_id
        if scrap.state != "done":
            raise UserError(_("Only done scraps can be unscrapped."))
        self._check_qty()
        scrap._run_unscrap(self.qty, self.to_location_id, self.note, self.reason)

        return {"type": "ir.actions.act_window_close"}
