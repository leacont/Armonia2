# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round


class StockScrapReasonTag(models.Model):
    _inherit = "stock.scrap.reason.tag"

    code = fields.Char(string="Reason Code", index=True)
    category_id = fields.Many2one(
        "scrap.category",
        string="Category",
        ondelete="set null",
    )


class StockScrap(models.Model):
    _inherit = "stock.scrap"

    scrap_qty = fields.Float(default=0.0)

    multi_scrap_category_ids = fields.Many2many(
        "scrap.category",
        "stock_scrap_multi_category_rel",
        "scrap_id",
        "category_id",
        string="Multi Scrap Categories",
        help="Selecting categories preloads all reasons from the selected categories.",
    )
    reason_line_ids = fields.One2many(
        "stock.scrap.reason.line",
        "scrap_id",
        string="Reason Split",
    )
    reason_line_summary = fields.Char(
        string="Reason Summary",
        compute="_compute_reason_line_summary",
    )
    scrap_category_summary = fields.Char(
        string="Scrap Category",
        compute="_compute_scrap_category_summary",
    )
    root_cause = fields.Char(string="Root Cause")
    corrective_action = fields.Text(string="Corrective Action")
    reference_code = fields.Char(string="Reference Code")
    unscrap_reason = fields.Char(string="Unscrap Reason", readonly=True, copy=False)

    unscrap_line_ids = fields.One2many(
        "stock.scrap.unscrap.line",
        "scrap_id",
        string="Unscrap History",
        readonly=True,
    )
    unscrap_qty_total = fields.Float(
        string="Unscrapped Qty",
        compute="_compute_unscrap_metrics",
        digits="Product Unit of Measure",
    )
    unscrap_qty_available = fields.Float(
        string="Available to Unscrap",
        compute="_compute_unscrap_metrics",
        digits="Product Unit of Measure",
    )
    can_unscrap = fields.Boolean(string="Can Unscrap", compute="_compute_unscrap_metrics")
    stock_balance_before = fields.Float(
        string="Stock Before Scrap",
        compute="_compute_stock_balance_projection",
        digits="Product Unit of Measure",
        help="Available quantity at source location before validating this scrap.",
    )
    stock_balance_after = fields.Float(
        string="Projected Stock After Scrap",
        compute="_compute_stock_balance_projection",
        digits="Product Unit of Measure",
        help="Projected available quantity at source location after applying scrap quantity.",
    )

    @api.onchange("reason_line_ids", "reason_line_ids.allocated_qty")
    def _onchange_reason_lines_set_scrap_qty(self):
        """Use split lines as source of truth for quantity in draft."""
        for scrap in self:
            if scrap.state != "draft":
                continue
            lines = scrap.reason_line_ids.filtered(lambda l: l.reason_id and l.allocated_qty > 0)
            total = sum(lines.mapped("allocated_qty"))
            if scrap.product_uom_id and not scrap.product_uom_id.is_zero(total):
                scrap.scrap_qty = total

    def _format_line_qty(self, qty):
        self.ensure_one()
        if not self.product_uom_id:
            return str(qty)
        rounded = float_round(qty, precision_rounding=self.product_uom_id.rounding)
        return f"{rounded:g} {self.product_uom_id.name}".strip()

    @api.depends(
        "reason_line_ids.reason_id",
        "reason_line_ids.allocated_qty",
        "scrap_reason_tag_ids",
        "unscrap_reason",
    )
    def _compute_reason_line_summary(self):
        for scrap in self:
            parts = []
            for line in scrap.reason_line_ids.sorted(lambda l: (l.sequence, l.id)):
                if not line.reason_id:
                    continue
                parts.append(line.reason_id.display_name)
            if not parts and scrap.scrap_reason_tag_ids:
                parts = scrap.scrap_reason_tag_ids.mapped("display_name")
            if not parts and scrap.unscrap_reason:
                parts = [scrap.unscrap_reason]
            scrap.reason_line_summary = ", ".join(parts) if parts else ""

    @api.depends("reason_line_ids.category_id", "scrap_reason_tag_ids.category_id")
    def _compute_scrap_category_summary(self):
        for scrap in self:
            category = False
            line = scrap.reason_line_ids.sorted(lambda l: (l.sequence, l.id)).filtered(lambda l: l.reason_id)[:1]
            if line and line.category_id:
                category = line.category_id
            elif scrap.scrap_reason_tag_ids:
                category = scrap.scrap_reason_tag_ids.mapped("category_id")[:1]
            scrap.scrap_category_summary = category.display_name if category else ""

    @api.depends("state", "scrap_qty", "product_uom_id", "unscrap_line_ids.qty")
    def _compute_unscrap_metrics(self):
        for scrap in self:
            total = sum(scrap.unscrap_line_ids.mapped("qty"))
            remaining = max(scrap.scrap_qty - total, 0.0)
            scrap.unscrap_qty_total = total
            scrap.unscrap_qty_available = remaining
            scrap.can_unscrap = (
                scrap.state == "done"
                and bool(scrap.product_uom_id)
                and (not scrap.product_uom_id.is_zero(remaining))
            )

    @api.depends(
        "product_id",
        "product_uom_id",
        "scrap_qty",
        "location_id",
        "lot_id",
        "package_id",
        "owner_id",
    )
    def _compute_stock_balance_projection(self):
        for scrap in self:
            if not scrap.product_id or not scrap.product_uom_id or not scrap.location_id:
                scrap.stock_balance_before = 0.0
                scrap.stock_balance_after = 0.0
                continue

            available_in_product_uom = scrap.with_context(
                location=scrap.location_id.id,
                lot_id=scrap.lot_id.id,
                package_id=scrap.package_id.id,
                owner_id=scrap.owner_id.id,
                strict=True,
            ).product_id.qty_available
            available_in_scrap_uom = scrap.product_id.uom_id._compute_quantity(
                available_in_product_uom, scrap.product_uom_id
            )
            scrap.stock_balance_before = available_in_scrap_uom
            scrap.stock_balance_after = available_in_scrap_uom - scrap.scrap_qty

    @api.onchange("multi_scrap_category_ids")
    def _onchange_multi_scrap_category_ids(self):
        for scrap in self:
            if scrap.multi_scrap_category_ids:
                scrap._load_reasons_from_category()

    def _load_reasons_from_category(self):
        for scrap in self:
            categories = scrap.multi_scrap_category_ids
            if not categories:
                continue
            reasons = self.env["stock.scrap.reason.tag"].search(
                [("category_id", "in", categories.ids)],
                order="sequence, id",
            )
            existing_allocated = {line.reason_id.id: line.allocated_qty for line in scrap.reason_line_ids}
            lines_cmd = [(5, 0, 0)]
            for reason in reasons:
                lines_cmd.append(
                    (0, 0, {
                        "reason_id": reason.id,
                        "allocated_qty": existing_allocated.get(reason.id, 0.0),
                    })
                )
            scrap.reason_line_ids = lines_cmd

    def action_load_reasons_from_category(self):
        for scrap in self:
            scrap._load_reasons_from_category()
        return True

    def write(self, vals):
        res = super().write(vals)
        if "reason_line_ids" in vals:
            for scrap in self.filtered(lambda s: s.state == "draft"):
                lines = scrap.reason_line_ids.filtered(lambda l: l.reason_id and l.allocated_qty > 0)
                total = sum(lines.mapped("allocated_qty"))
                if scrap.product_uom_id and not scrap.product_uom_id.is_zero(total):
                    super(StockScrap, scrap).write({"scrap_qty": total})
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for scrap in records.filtered(lambda s: s.state == "draft"):
            lines = scrap.reason_line_ids.filtered(lambda l: l.reason_id and l.allocated_qty > 0)
            total = sum(lines.mapped("allocated_qty"))
            if scrap.product_uom_id and not scrap.product_uom_id.is_zero(total):
                super(StockScrap, scrap).write({"scrap_qty": total})
        return records

    @api.constrains("reason_line_ids", "scrap_qty", "product_uom_id")
    def _check_reason_lines_qty_total(self):
        if self.env.context.get("skip_reason_split_check"):
            return
        for scrap in self:
            lines = scrap.reason_line_ids.filtered(lambda l: l.reason_id)
            if not lines:
                continue
            if not scrap.product_uom_id or scrap.product_uom_id.is_zero(scrap.scrap_qty):
                continue
            total = sum(lines.mapped("allocated_qty"))
            if scrap.product_uom_id.is_zero(total):
                raise ValidationError(
                    _(
                        "In scrap %(name)s, reason split has zero total. "
                        "The split must sum %(qty)s.",
                        name=scrap.display_name,
                        qty=scrap._format_line_qty(scrap.scrap_qty),
                    )
                )
            if scrap.product_uom_id.compare(total, scrap.scrap_qty) != 0:
                raise ValidationError(
                    _(
                        "Reason split total (%(total)s) must match scrap quantity (%(scrap_qty)s) in %(name)s.",
                        total=scrap._format_line_qty(total),
                        scrap_qty=scrap._format_line_qty(scrap.scrap_qty),
                        name=scrap.display_name,
                    )
                )

    def action_open_unscrap_wizard(self):
        self.ensure_one()
        if self.state != "done":
            raise UserError(_("Only done scraps can be unscrapped."))
        if self.product_uom_id.is_zero(self.unscrap_qty_available):
            raise UserError(_("No remaining quantity is available to unscrap."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Unscrap"),
            "res_model": "stock.scrap.unscrap.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_scrap_id": self.id,
                "default_qty": self.unscrap_qty_available,
                "default_to_location_id": self.location_id.id,
            },
        }

    def _run_unscrap(self, qty, to_location, note=None, reason=None):
        """Reverse current scrap by creating and validating an inverse scrap."""
        self.ensure_one()
        if self.state != "done":
            raise UserError(_("Only done scraps can be unscrapped."))
        if not self.product_uom_id:
            raise UserError(_("Missing UoM on scrap record."))
        if self.product_uom_id.compare(qty, self.unscrap_qty_available) > 0:
            raise UserError(
                _(
                    "Unscrap quantity (%(qty)s) cannot exceed remaining available (%(available)s).",
                    qty=qty,
                    available=self.unscrap_qty_available,
                )
            )

        unscrap_ref = f"Unscrap-{self.name}"
        reverse_scrap = self.with_context(skip_reason_split_check=True).create({
            "company_id": self.company_id.id,
            "origin": self.origin or self.name,
            "product_id": self.product_id.id,
            "product_uom_id": self.product_uom_id.id,
            "lot_id": self.lot_id.id,
            "package_id": self.package_id.id,
            "owner_id": self.owner_id.id,
            "location_id": self.scrap_location_id.id,
            "scrap_location_id": to_location.id,
            "scrap_qty": qty,
            "should_replenish": False,
            "unscrap_reason": reason,
        })
        reverse_scrap.do_scrap()
        vals_done = {
            "name": unscrap_ref,
            "origin": unscrap_ref,
            "reference_code": unscrap_ref,
            "scrap_qty": -abs(qty),
        }
        if reverse_scrap.state != "done":
            vals_done.update({
                "state": "done",
                "date_done": fields.Datetime.now(),
            })
        reverse_scrap.write(vals_done)
        if reverse_scrap.state != "done":
            raise UserError(
                _(
                    "Unscrap %(ref)s was created but not confirmed.",
                    ref=unscrap_ref,
                )
            )

        move_id = False
        if "move_ids" in reverse_scrap._fields and reverse_scrap.move_ids:
            move_id = reverse_scrap.move_ids[:1].id
        elif "move_id" in reverse_scrap._fields and reverse_scrap.move_id:
            move_id = reverse_scrap.move_id.id

        self.env["stock.scrap.unscrap.line"].create({
            "scrap_id": self.id,
            "move_id": move_id,
            "qty": qty,
            "reason": reason or _("Unspecified"),
            "from_location_id": self.scrap_location_id.id,
            "to_location_id": to_location.id,
            "lot_id": self.lot_id.id,
            "note": note,
        })
        return reverse_scrap

    def action_unscrap_full(self):
        """
        Reverse done scraps for full available quantity.
        Useful from list view Action menu as one-click "negative scrap".
        """
        if len(self) != 1:
            raise UserError(_("Select exactly one scrap record to run Unscrap."))
        scrap = self
        if scrap.state != "done":
            raise UserError(_("Only done scraps can be unscrapped."))
        if scrap.scrap_qty < 0:
            raise UserError(_("This record is already an Unscrap and cannot be unscrapped again."))
        if not scrap.product_uom_id or scrap.product_uom_id.is_zero(scrap.unscrap_qty_available):
            raise UserError(
                _("Scrap %(name)s has no remaining quantity available to unscrap.", name=scrap.display_name)
            )

        qty = scrap.unscrap_qty_available
        scrap._run_unscrap(
            qty,
            scrap.location_id,
            _("Auto full unscrap from list action"),
            _("Full unscrap"),
        )

        return {"type": "ir.actions.client", "tag": "reload"}

    def action_validate(self):
        """
        Multi-scrap behavior:
        if split lines have multiple reasons with qty > 0, create one scrap record per reason.
        """
        self.ensure_one()
        if self.state != "draft":
            return super().action_validate()

        lines = self.reason_line_ids.filtered(lambda l: l.reason_id and l.allocated_qty > 0)
        if not lines:
            return super().action_validate()
        for line in lines:
            vals = {
                "company_id": self.company_id.id,
                "origin": self.origin,
                "product_id": self.product_id.id,
                "product_uom_id": self.product_uom_id.id,
                "lot_id": self.lot_id.id,
                "package_id": self.package_id.id,
                "owner_id": self.owner_id.id,
                "location_id": self.location_id.id,
                "scrap_location_id": self.scrap_location_id.id,
                "scrap_qty": line.allocated_qty,
                "should_replenish": self.should_replenish,
                "picking_id": self.picking_id.id,
                "reference_code": self.reference_code,
                "root_cause": self.root_cause,
                "corrective_action": self.corrective_action,
                "multi_scrap_category_ids": [(6, 0, self.multi_scrap_category_ids.ids)],
                "scrap_reason_tag_ids": [(6, 0, line.reason_id.ids)],
                "reason_line_ids": [(0, 0, {
                    "reason_id": line.reason_id.id,
                    "allocated_qty": line.allocated_qty,
                    "note": line.note,
                })],
            }
            child = self.with_context(skip_reason_split_check=True).create(vals)
            super(StockScrap, child).action_validate()
        # Discard draft container record to avoid stale references in form.
        if self.exists() and self.state == "draft":
            self.unlink()
        return self.env["ir.actions.act_window"]._for_xml_id("stock.action_stock_scrap")
