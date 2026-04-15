# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

SKIP_CONTEXT = "skip_bom_multilevel_propagate"


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    project_number = fields.Char(string="Project Number", readonly=True, copy=False)

    x_studio_ruter_id = fields.Integer(string="Router ID")
    x_studio_job_number = fields.Char(string="Job Number")
    x_studio_sales_order = fields.Many2one("sale.order", string="Sales Order")

    MAX_PROPAGATION_LEVEL = 25

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("project_number"):
                continue
            if vals.get("origin"):
                parent = self.env["mrp.production"].search([("name", "=", vals["origin"])], limit=1)
                if parent and parent.project_number:
                    vals["project_number"] = parent.project_number
            if not vals.get("project_number"):
                seq = self.env["ir.sequence"].next_by_code("project.number")
                if not seq:
                    raise UserError(
                        _(
                            "Could not get a project number: sequence with code 'project.number' is missing. "
                            "Upgrade the Multilevel BOM module or create the sequence."
                        )
                    )
                vals["project_number"] = seq
        return super().create(vals_list)

    def action_propagate_router(self):
        """Manual propagation entry point (e.g. server actions)."""
        for mo in self:
            if not mo.bom_id:
                raise UserError(_("Manufacturing order %s has no bill of materials.") % mo.name)
            mo._propagate_children(mo, current_level=1, start_base=mo.date_start)
        return True

    def _multilevel_bom_find(self, product, bom_type=False):
        """BoM lookup aligned with MO rules: company, operation type; bom_type False = any type."""
        self.ensure_one()
        return self.env["mrp.bom"].with_context(active_test=True)._bom_find(
            product,
            picking_type=self.picking_type_id,
            company_id=self.company_id.id,
            bom_type=bom_type,
        )

    def _multilevel_bom_resolve(self, product):
        """Prefer a normal manufacturing BoM; otherwise use Odoo resolution (e.g. phantom)."""
        self.ensure_one()
        m = self._multilevel_bom_find(product, bom_type="normal")
        b = m.get(product)
        if b and b.ids:
            return b
        m2 = self._multilevel_bom_find(product, bom_type=False)
        b2 = m2.get(product) if m2 else None
        return b2 if (b2 and b2.ids) else self.env["mrp.bom"]

    def _process_bom_component(
        self,
        parent_mo,
        product,
        qty_needed,
        product_uom,
        current_level,
        start_base,
    ):
        """
        Create a manufacturing order for ``product`` when it has a manufacturing BoM, or expand
        a phantom (kit) BoM without creating an MO for the kit. Returns MOs created in this branch.
        """
        created = self.env["mrp.production"]
        if not product or qty_needed <= 0:
            return created

        sub_bom = parent_mo._multilevel_bom_resolve(product)
        if not sub_bom or not sub_bom.ids:
            return created

        btype = getattr(sub_bom, "type", False)
        if btype in ("subcontract", "subcontracting"):
            _logger.info(
                "Multilevel BOM: skipping subcontracting for %s (MO %s)",
                product.display_name,
                parent_mo.name,
            )
            return created

        bom_ref = sub_bom.product_qty or 1.0
        if bom_ref <= 0:
            bom_ref = 1.0

        if btype == "phantom":
            scale = qty_needed / bom_ref
            for pline in sub_bom.bom_line_ids:
                if not pline.product_id:
                    continue
                if pline._skip_bom_line(product):
                    continue
                line_qty = pline.product_qty * scale
                if line_qty <= 0:
                    continue
                pu = pline.product_uom_id or pline.product_id.uom_id
                created |= self._process_bom_component(
                    parent_mo,
                    pline.product_id,
                    line_qty,
                    pu,
                    current_level,
                    start_base,
                )
            return created

        if self.search_count(
            [
                ("origin", "=", parent_mo.name),
                ("product_id", "=", product.id),
            ]
        ):
            return created

        uom_id = product_uom.id if product_uom else product.uom_id.id

        router_id = parent_mo.x_studio_ruter_id
        job_num = parent_mo.x_studio_job_number or False
        sale_obj = parent_mo.x_studio_sales_order
        sale_id = sale_obj.id if sale_obj else False

        vals = {
            "product_id": product.id,
            "bom_id": sub_bom.id,
            "product_qty": qty_needed,
            "product_uom_id": uom_id,
            "origin": parent_mo.name,
            "x_studio_ruter_id": router_id,
            "x_studio_job_number": job_num,
            "x_studio_sales_order": sale_id,
            "company_id": parent_mo.company_id.id,
        }
        if parent_mo.picking_type_id:
            vals["picking_type_id"] = parent_mo.picking_type_id.id
        if start_base:
            vals["date_start"] = start_base

        Mo = self.env["mrp.production"]
        child = Mo.create(vals)
        child.with_context(**{SKIP_CONTEXT: True}).action_confirm()
        _logger.info("Multilevel BOM: child MO %s from %s", child.name, parent_mo.name)
        return child

    def _propagate_children(self, parent_mo, current_level, start_base=None):
        if current_level > self.MAX_PROPAGATION_LEVEL:
            _logger.warning(
                "Multilevel BOM: max depth (%s) reached for MO %s",
                self.MAX_PROPAGATION_LEVEL,
                parent_mo.name,
            )
            return

        if not parent_mo.bom_id:
            return

        parent_mo.ensure_one()

        bom_qty = parent_mo.bom_id.product_qty or 1.0
        if bom_qty <= 0:
            bom_qty = 1.0

        factor = parent_mo.product_qty / bom_qty
        new_children = self.env["mrp.production"]

        for line in parent_mo.bom_id.bom_line_ids:
            if not line.product_id:
                continue
            if line._skip_bom_line(parent_mo.product_id):
                continue

            qty = line.product_qty * factor
            if qty <= 0:
                continue

            pu = line.product_uom_id or line.product_id.uom_id
            new_children |= self._process_bom_component(
                parent_mo,
                line.product_id,
                qty,
                pu,
                current_level,
                start_base,
            )

        for child_mo in new_children:
            self._propagate_children(
                child_mo,
                current_level + 1,
                start_base=start_base or child_mo.date_start,
            )

    def action_confirm(self):
        res = super().action_confirm()
        if self.env.context.get(SKIP_CONTEXT):
            return res
        for mo in self:
            if not mo.bom_id:
                raise UserError(_("Manufacturing order %s has no bill of materials.") % mo.name)
            mo._propagate_children(mo, current_level=1, start_base=mo.date_start)
        return res
