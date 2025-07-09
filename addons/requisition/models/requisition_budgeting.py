# -*- coding: utf-8 -*-
from odoo import models, fields, api, _ 
from odoo.exceptions import ValidationError

class RequisitionBudgeting(models.Model):
    _name = 'requisition.budgeting'
    _inherit = ['mail.thread']
    _description = 'Budgeting for Requisitions'
    _order = "id,sequence"

    name = fields.Char(string="Name")
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=1)
    budget = fields.Monetary('Budget', tracking=True, currency_field='currency_id')
    range_type_id = fields.Many2one('date.range.type', string='Period')
    purchase_type_id = fields.Many2one('purchase.type', string='Purchase Type')
    level = fields.Selection([
        ('general', 'General'),
        ('administrative', 'Administrative'), 
        ('maintenance', 'Maintenance')], 
        string='Level', required=True, default='general')
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, readonly=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                required=True, readonly=True,
                                default=lambda self: self.env.company.currency_id.id)
    budget_line_ids = fields.One2many('requisition.budgeting.line', 'budgeting_id')
    requisition_mail_ids = fields.One2many('requisition.mail', 'budgeting_id')
    sequence_id = fields.Many2one('ir.sequence', 'Sequence')
    is_quota = fields.Boolean(string='Is Quota', default=False)
    amount_quota = fields.Float(string='Max Amount', help="Enter the percentage value in decimals")
    number_quota = fields.Integer(string='NNumber of Quotas', help="Enter the number of quotas")

    @api.onchange('is_quota')
    def onchange_is_quota(self):
        if not self.is_quota:
            self.amount_quota = None
            self.number_quota = None

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record.sequence_id = record._create_requisition_sequence()
        return records

    def _create_requisition_sequence(self):
        for record in self:
            company_name = record.company_id.name[:3].upper()
            requisition_type_name = record.name[:3].upper()
            if not requisition_type_name:
                raise ValidationError(_('The requisition name cannot be empty.'))
            requisition_vals ={
                'name': f'requisition {record.name}',
                'code': f'requisition {record.name}',
                'company_id': record.company_id.id,
                'prefix': f'{company_name}-REQ/{requisition_type_name}/%(range_year)s/',
                'padding': 3,
                'number_next': 1,
                'number_increment': 1
            }
            return record.env['ir.sequence'].create(requisition_vals).id

class RequisitionBudgetLine(models.Model):
    _name = 'requisition.budgeting.line'
    _description = 'Budget Lines for Requisitions'
    _order = "id,sequence"

    def _default_category_id(self):
        if self.env.context.get('active_model') == 'product.category':
            return self.env.context.get('active_id')

    def _default_product_id(self):
        if self.env.context.get('active_model') == 'product.template' and self.env.context.get('active_id'):
            product_template = self.env['product.template'].browse(self.env.context.get('active_id'))
            product_template = product_template.exists()
            if product_template.product_variant_count == 1:
                return product_template.product_variant_id
        elif self.env.context.get('active_model') == 'product.product':
            return self.env.context.get('active_id')

    budgeting_id = fields.Many2one('requisition.budgeting')
    product_id = fields.Many2one(
        'product.product', 'Product', check_company=True,
        default=_default_product_id,
        domain="[('product_tmpl_id', '=', context.get('active_id', False))] if context.get('active_model') == 'product.template' else [('type', '!=', 'service')]",
        ondelete='cascade')
    category_id = fields.Many2one('product.category', 'Product Category',
        default=_default_category_id, domain=[('filter_for_stock_putaway_rule', '=', True)], ondelete='cascade')
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda s: s.env.company.id, index=True)
    active = fields.Boolean('Active', default=True)
    sequence = fields.Integer(default=1)
