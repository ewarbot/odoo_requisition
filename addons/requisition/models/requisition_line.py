# -*- coding: utf-8 -*-
from odoo import models, fields, api, _ 
from datetime import datetime
from odoo.exceptions import ValidationError, UserError, AccessError
import logging
from odoo.osv import expression
from odoo.tools.misc import unquote

class RequisitionLine(models.Model):
    _name = 'requisition.line'
    _inherit = ['mail.thread']
    _order='id desc'
    _description = 'Requisition Line'
    
    @api.model
    def _selection_quota(self):
        requisition_budgeting = self.env['requisition.budgeting'].sudo().search(
            [
                ('company_id', '=', self.env.company.id),
                ('is_quota', '=', True)
            ],
            limit=1
        )
        if not requisition_budgeting:
            return []
        number_quota = requisition_budgeting.number_quota
        return [(str(i), str(i)) for i in range(1, number_quota + 1)] if number_quota else []


    name = fields.Char(tracking=True, string="Description")
    requisition_id = fields.Many2one('requisition')
    requisition_budgeting_id = fields.Many2one('requisition.budgeting',  related="requisition_id.requisition_budgeting_id")
    company_id = fields.Many2one('res.company', related='requisition_id.company_id', string='Company', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='requisition_id.currency_id')
    state = fields.Selection(related='requisition_id.state', store=True)
    product_ids = fields.Many2many(
        'product.product',
        compute="_compute_get_ids",
        store=False
        )
    category_ids = fields.Many2many(
        'product.category',
        compute="_compute_get_ids",
        store=False
    )    
    product_domain_ids = fields.Many2many(
        'product.product',
        compute='_compute_product_domain_ids',
        store=False
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        domain="[('id', 'in', product_domain_ids)]"
    )
    quantity = fields.Float(string='Quantity', tracking=True, default=0)
    approved_quantity = fields.Float(string="Approved Quantity", tracking=True)
    unit_cost = fields.Monetary('Cost', tracking=True, compute= "_info_products", store=True, currency_field='currency_id')
    seller_id = fields.Many2one('res.partner', 'Supplier', 
                                domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", 
                                ondelete='cascade', tracking=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    sub_total = fields.Float('Subtotal', tracking=True, store=True, compute="_compute_sub_total")
    observation = fields.Text('Requisition Observation')
    observation_purchase = fields.Text('Purchase Observation') 
    purchased_product = fields.Boolean(default=False)
    select_quota = fields.Selection(selection=_selection_quota, string="Quotas")
    paid_quota = fields.Integer(default=0)
    pending_quota = fields.Integer(compute="_calculate_pending_quota", store=True)
    sub_total_quotas = fields.Float('Subtotal for Quotas', tracking=True, compute="_calculate_subtotal", store=True)
    product_quota = fields.Boolean(default=False)
    string_quota = fields.Char(string="Paid Quotas", compute="_compute_string_quota", store=True)

    @api.depends('requisition_budgeting_id')
    def _compute_get_ids(self):
        for rec in self:
            budget_lines = rec.requisition_budgeting_id.budget_line_ids
            rec.product_ids = budget_lines.mapped('product_id')
            rec.category_ids = budget_lines.mapped('category_id')

    @api.depends('product_ids', 'category_ids')
    def _compute_product_domain_ids(self):
        Product = self.env['product.product']
        for rec in self:
            domain = [('purchase_ok', '=', True)]

            criteria = []
            if rec.category_ids:
                criteria.append(('categ_id', 'in', rec.category_ids.ids))
            if rec.product_ids:
                criteria.append(('id', 'in', rec.product_ids.ids))

            if len(criteria) == 2:
                domain += ['|'] + criteria
            elif len(criteria) == 1:
                domain += criteria

            rec.product_domain_ids = Product.search(domain)

    @api.depends('pending_quota','paid_quota')
    def _compute_string_quota(self):
        for record in self:
            record.string_quota = ''
            if record.select_quota:
                record.string_quota = f'{record.select_quota}/{record.paid_quota}'

    @api.depends('approved_quantity','product_uom_id')
    def _compute_sub_total(self):
        for record in self:
            record.sub_total = record.unit_cost * record.approved_quantity

    def get_latest_sales_price(self, sellers):
        data = [{'partner_id':s.partner_id.id, 'sequence':s.sequence} for s in sellers]
        seller_dict = max(data, key=lambda x: x["sequence"])
        seller = sellers.filtered(lambda x: x.partner_id.id == seller_dict['partner_id'])[0]
        return seller

    @api.model
    def _fix_tax_included_price_company(self, price, prod_taxes, line_taxes, company_id):
        if company_id:
            prod_taxes = prod_taxes.filtered(lambda tax: tax.company_id == company_id)
        return self._fix_tax_included_price(price, prod_taxes, line_taxes)
    
    @api.model
    def _fix_tax_included_price(self, price, prod_taxes, line_taxes=None):
        incl_tax = prod_taxes.filtered(lambda tax: tax.price_include)
        if incl_tax:
            return incl_tax.compute_all(price)['total_excluded']
        return price
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        self.product_uom_id = self.product_id.uom_po_id or self.product_id.uom_id
        self.name = self.product_id.name


    @api.depends('product_id', 'quantity')
    def _info_products(self):
        for record in self:
            if record.product_id:
                if record.quantity and record.state == 'draft':
                    record.approved_quantity = record.quantity
                if record.product_id.seller_ids:
                    seller = self.get_latest_sales_price(record.product_id.seller_ids)
                else: 
                    seller = False 
                if not seller:
                    raise ValidationError(_('The selected product does not have a configured provider. For more information, contact your system administrator.'))
                record.seller_id = seller.partner_id.id
                taxes_id=None
                unit_cost = record._fix_tax_included_price_company(seller.price, record.product_id.supplier_taxes_id, taxes_id, record.company_id) if seller else 0.0
                if unit_cost and seller and record.requisition_id.currency_id and seller.currency_id != record.requisition_id.currency_id:
                    unit_cost = seller.currency_id.compute(unit_cost, record.requisition_id.currency_id)
                if seller and record.product_uom_id and seller.product_uom != record.product_uom_id:
                    unit_cost = seller.product_uom._compute_price(unit_cost, record.product_uom_id)
                record.unit_cost = unit_cost

    @api.depends('select_quota','approved_quantity','product_uom_id')
    def _calculate_subtotal(self):
        for record in self:
            record.sub_total = record.unit_cost * record.approved_quantity
            if record.requisition_budgeting_id.is_quota:
                record.sub_total_quotas = record.sub_total
                if record.select_quota:
                    record.sub_total_quotas = (record.unit_cost * record.approved_quantity) / int(record.select_quota)

    @api.depends('select_quota')
    def _calculate_pending_quota(self):                
        for record in self:      
            if record.requisition_budgeting_id.is_quota:      
                if record.paid_quota == 0:
                    record.paid_quota=1
                record.pending_quota = int(record.select_quota) - record.paid_quota

    def unlink(self):
        for record in self:
            if record.parent_id.state in ('approved', 'budgeted'):
                raise UserError(
                    _('Cannot delete lines when the requisition is approved.')
                )
        return super(RequisitionLine, self).unlink()