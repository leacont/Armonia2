# -*- coding: utf-8 -*-

from odoo import fields, models


class StockScrapUnscrapLine(models.Model):
    _name = "stock.scrap.unscrap.line"
    _description = "Unscrap History Line"
    _order = "id desc"

    scrap_id = fields.Many2one(
        "stock.scrap",
        string="Scrap",
        required=True,
        ondelete="cascade",
        index=True,
    )
    move_id = fields.Many2one("stock.move", string="Generated Move", readonly=True, ondelete="set null")
    qty = fields.Float(string="Unscrap Qty", digits="Product Unit of Measure", required=True)
    reason = fields.Char(string="Reason", readonly=True)
    from_location_id = fields.Many2one("stock.location", string="From", readonly=True)
    to_location_id = fields.Many2one("stock.location", string="To", readonly=True)
    lot_id = fields.Many2one("stock.lot", string="Lot/Serial", readonly=True)
    user_id = fields.Many2one("res.users", string="User", readonly=True, default=lambda self: self.env.user)
    note = fields.Char(string="Note", readonly=True)
    date_done = fields.Datetime(string="Date", readonly=True, default=fields.Datetime.now)
