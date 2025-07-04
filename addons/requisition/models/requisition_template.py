# -*- coding: utf-8 -*-
from odoo import models, fields, api

class RequisitionTemplate(models.Model):
    _name = 'requisition.template'
    _inherit = ['mail.thread']
    _description = "Plantilla de requisiciones"

    name = fields.Char('Nombre', tracking=True, required=True)
    active = fields.Boolean(default=True)
    requisition_budgeting_id = fields.Many2one('requisition.budgeting',  string='Tipo de Requisición')
    company_id = fields.Many2one('res.company', string='Compañia',
                                 required=True, readonly=True,
                                 default=lambda self: self.env.company)
    requisition_tmpl_line_id = fields.One2many('requisition.template.line', 'requisition_tmpl_id')

class RequisitionTemplateLine(models.Model):
    _name = 'requisition.template.line'
    _description = "Lineas de plantilla de requisiciones"

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
    product_id = fields.Many2one(
        'product.product', 
        string='Producto',
        domain="[('purchase_ok', '=', True), '|',('categ_id', 'in', category_ids), ('id', 'in', product_ids)]"
    )