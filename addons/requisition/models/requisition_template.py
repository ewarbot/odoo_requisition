# -*- coding: utf-8 -*-
from odoo import models, fields, api

class RequisitionTemplate(models.Model):
    _name = 'requisition.template'
    _inherit = ['mail.thread']
    _description = "Requisition Template"

    name = fields.Char('Name', tracking=True, required=True)
    active = fields.Boolean(default=True)
    requisition_budgeting_id = fields.Many2one('requisition.budgeting',  string='Requisition Type')
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, readonly=True,
                                 default=lambda self: self.env.company)
    requisition_tmpl_line_id = fields.One2many('requisition.template.line', 'requisition_tmpl_id')

class RequisitionTemplateLine(models.Model):
    _name = 'requisition.template.line'
    _description = "Requisition Template Lines"

    @api.depends('requisition_budgeting_id')
    def _compute_get_ids(self):
        for rec in self:
            budget_line = rec.requisition_budgeting_id.budget_line_ids
            rec.product_ids = budget_line.mapped('product_id')
            rec.category_ids = budget_line.mapped('category_id')

    requisition_tmpl_id = fields.Many2one('requisition.template')
    requisition_budgeting_id = fields.Many2one(
        'requisition.budgeting',  
        related="requisition_tmpl_id.requisition_budgeting_id"
        )
    company_id = fields.Many2one(
        'res.company', 
        related='requisition_tmpl_id.company_id', 
        string='Company', 
        store=True, 
        readonly=True
        )
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
        string='Producto',
        domain="[('id', 'in', product_domain_ids)]"
    )

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
