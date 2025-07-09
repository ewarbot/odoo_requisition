# -*- coding: utf-8 -*-
from odoo import models, fields, api, _ 
from odoo.exceptions import ValidationError
import logging
from itertools import groupby
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from .data import STATE_LIST, LEVEL_LIST, STATE_TO_STATUS

class Requisition(models.Model):
    _name = 'requisition'
    _inherit = ['mail.thread']
    _order='period_id desc'
    _description = 'Requisition'


    name = fields.Char('Name', default='*')
    requisition_budgeting_id = fields.Many2one('requisition.budgeting',  string='Requisition Type')
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, readonly=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                required=True, readonly=True,
                                default=lambda self: self.env.company.currency_id.id)
    active = fields.Boolean(default=True, tracking=True)
    requisition_date = fields.Datetime(string='Requisition Creation Date', readonly=True, index=True, default=fields.Datetime.now, copy=False)
    state = fields.Selection(STATE_LIST, string='State', required=True, readonly=True, default='draft', tracking=True)
    requisition_line_ids = fields.One2many('requisition.line', 'requisition_id')
    budget = fields.Monetary('Budget', currency_field='currency_id', copy=False)
    total_requisition = fields.Monetary('Total Requisition', tracking=True, compute="_compute_total", store=True, currency_field='currency_id')
    difference_value = fields.Monetary('Available Balance', tracking=True, compute="_compute_difference", currency_field='currency_id')
    purchase_order_ids = fields.One2many('purchase.order', 'requisition_id', copy=False)
    purchase_order_count = fields.Integer(string="Purchase Orders", compute="_compute_purchase_count", tracking=True, copy=False)
    partner_id = fields.Many2one('res.partner', string='Responsible', tracking=True, default=lambda self: self.env.user.partner_id.id, copy=False)
    range_type_id = fields.Many2one('date.range.type', string='Period Type')
    period_id = fields.Many2one('date.range', string="Period", tracking=True, 
    domain="[('type_id','=', range_type_id),('date_end','>=',requisition_date)]", copy=False)
    level = fields.Selection(LEVEL_LIST, string='Level', tracking=True)
    notes = fields.Text('Notes', tracking=True)    
    confirm_by = fields.Char('Confirmed By', readonly=True, copy=False)
    date_confirm = fields.Date('Confirmation Date', readonly=True, copy=False)
    approver_by = fields.Char('Approved By', readonly=True, copy=False)
    date_approve = fields.Date('Approval Date', readonly=True, copy=False)
    is_quota = fields.Boolean(string='Is Quota', related='requisition_budgeting_id.is_quota', store=True)
    requisition_status = fields.Char(
            string='Requisition Status',
            compute='_compute_requisition_status',
            store=True
        )
    requisition_tmpl_id = fields.Many2one('requisition.template',string='Requisition Template', ondelete='cascade')

    @api.onchange('requisition_tmpl_id')
    def onchange_requisition_tmpl(self):
        self.requisition_line_ids = [(5, 0, 0)]
        
        if self.is_quota:
            self._add_quotas_lines_onchange()
        
        if self.requisition_tmpl_id:
            self.requisition_line_ids = [
                (0, 0, {'product_id': product_id})
                for product_id in self.requisition_tmpl_id.requisition_tmpl_line_id.mapped('product_id.id')
            ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.name == '*':
                name_sequence = f'requisition {record.requisition_budgeting_id.name}'
                record.name = self.env['ir.sequence'].next_by_code(name_sequence) or '/'
        return records

    @api.depends('purchase_order_ids')
    def _compute_purchase_count(self):
        for record in self:
            record.purchase_order_count = len(record.purchase_order_ids)

    @api.depends('state')
    def _compute_requisition_status(self):
        """Field computed for the requisition status"""
        for record in self:
            record.requisition_status = STATE_TO_STATUS.get(record.state)
            record.send_mail()

    def unlink(self):
        for record in self:
            record.update_lines()
            record.requisition_line_ids.unlink()
            record.purchase_order_ids.unlink()
        return super(Requisition, self).unlink()

    @api.onchange('requisition_budgeting_id')
    def _onchange_requisition_budgeting(self):
        if self.requisition_budgeting_id:
            self.range_type_id = self.requisition_budgeting_id.range_type_id.id
            self.level = self.requisition_budgeting_id.level
            self.budget = self.requisition_budgeting_id.budget
            self.requisition_tmpl_id = None
            self.requisition_line_ids = [(5, 0, 0)]
            if self.is_quota:
                self._add_quotas_lines_onchange()

    @api.depends('requisition_line_ids.sub_total')
    def _compute_total(self):
        for record in self:
            record.total_requisition = sum(record.requisition_line_ids.mapped('sub_total'))

    @api.depends('requisition_line_ids.sub_total')
    def _compute_difference(self):
        for record in self:
            total_line = sum([line.sub_total_quotas if line.product_quota else line.sub_total for line in record.requisition_line_ids ])   
            record.difference_value = record.budget - total_line

    @api.onchange('period_id', 'requisition_budgeting_id')
    def _onchange_period_id(self):
        """
        This method is triggered when period_id or requisition_budgeting_id changes.
        Sets range_type_id based on the selected requisition_budgeting_id.
        """
        if not self.period_id or not self.requisition_budgeting_id or self.level == 'administrative':
            return
        Requisition = self.env['requisition']
        error_messages = []
        base_domain = [
            ('company_id', '=', self.company_id.id),
            ('requisition_budgeting_id', '=', self.requisition_budgeting_id.id)
        ]
        if self.level == 'maintenance':
            maintenance_domain = base_domain + [
                ('state', 'in', ('draft', 'rerejected', 'confirmed'))
            ]   
            existing_req = Requisition.search(maintenance_domain, limit=1)
            if existing_req:
                error_messages.append(
                    "Cannot generate another maintenance requisition while one is in progress: "
                    f"{existing_req.name} (Status: {existing_req.state})"
                )
        period_domain = base_domain + [
            ('period_id', '=', self.period_id.id),
            ('state', '!=', 'canceled')
        ]
        existing_period_reqs = Requisition.search(period_domain)
        if len(existing_period_reqs) >= 1:
            req_names = ", ".join(existing_period_reqs.mapped('name'))
            error_messages.append(
                "Only one requisition can be created per period. "
                f"Existing: {req_names}"
            )
        if error_messages:
            error_title = "Requisition Validation"
            full_message = f"{error_title}\n\n" + "\n\n- ".join(error_messages)
            return {
                'warning': {
                    'title': error_title,
                    'message': full_message
                }
            }

    def action_open_purchase(self):
        purchase_ids = self.purchase_order_ids.ids
        action = self.env.ref("purchase.purchase_form_action").read()[0]
        context = {
            "create": False,
            "edit": False,
        }
        action["context"] = context
        action["name"] = _("Ordenes de compra")
        view_tree_id = self.env.ref(
            "purchase.purchase_order_view_tree"
        ).id
        view_form_id = self.env.ref(
            "purchase.purchase_order_form"
        ).id
        action["view_mode"] = "form"
        action["views"] = [(view_form_id, "form")]
        action["res_id"] = purchase_ids[0]
        if len(purchase_ids) > 1:
            action["view_mode"] = "list,form"
            action["views"] = [(view_tree_id, "list"), (view_form_id, "form")]
            action["domain"] = [("id", "in", purchase_ids)]

        return action   
    
    def action_confirm(self):
        """Validate and confirm the requisition optimizing resources"""
        self.ensure_one()

        if not self.requisition_line_ids:
            raise ValidationError("Cannot confirm a requisition without products")

        today = fields.Date.context_today(self)
        
        if today < self.period_id.date_start:
            raise ValidationError("Cannot confirm a requisition from a future period")

        self.zero_product_control()
        
        self.write({
            'state': 'confirmed',
            'confirm_by': self.env.user.name,
            'date_confirm': today
        })

    def action_approve(self):
        today = fields.Date.context_today(self)
        self.write({
            'state': 'approved',
            'approver_by': self.env.user.name,
            'date_approve': today
        })

    def action_rejected(self):
        self.write({
            'state': 'rejected'
        })

    def action_cancel(self):
        """Cancels the requisition optimizing resources"""
        self.update_lines()
        self.write({
            'state': 'canceled'
        })

    def zero_product_control(self):
        """Verifies lines with zero quantity in batch"""
        if self.requisition_line_ids.filtered(lambda l: l.quantity <= 0):
            raise ValidationError('Cannot send products with quantity less than or equal to 0')

    def compare_query(self):               
        for record in self:
            list_obj=[]
            for line in record.requisition_line_ids:     
                obj_lines = self.env['requisition.line'].search([  ('quotas_id','=',line.quotas_id.id),
                                                                    ('quotas_done','=',line.quotas_done),
                                                                    ('state','!=','canceled'),
                                                                    ('requisition_id.id','!=',record.id),
                                                                    ('sub_total_quotas','=',line.sub_total_quotas),
                                                                    ('product_id','=',line.product_id.id),
                                                                    ('seller_id','=',line.seller_id.id),                                              
                                                                ])
                if obj_lines:
                    list_obj.append(obj_lines)
        if list_obj and len(list_obj) > 0:
            return True
        return False

    def compare_query(self):
        """Verifies existence of duplicate lines in an optimized way"""
        self.ensure_one()
        
        domains = []
        for line in self.requisition_line_ids:
            domains.append([
                ('quotas_id', '=', line.quotas_id.id),
                ('quotas_done', '=', line.quotas_done),
                ('state', '!=', 'canceled'),
                ('requisition_id', '!=', self.id),
                ('sub_total_quotas', '=', line.sub_total_quotas),
                ('product_id', '=', line.product_id.id),
                ('seller_id', '=', line.seller_id.id)
            ])
        
        return bool(domains) and self.env['requisition.line'].search_count(
            ['|'] * (len(domains) - 1) + domains,
            limit=1
        ) > 0

    def action_give_back(self):
        """Optimized handling of reverting to draft"""
        for record in self:
            record.write({
                'state': 'draft',
                'confirm_by': False,
                'date_confirm': False,
                'approver_by': False,
                'date_approve': False
            })

    def update_lines(self, cond=False):
        """Updates requisition lines using ORM in an optimized way"""
        if not self:
            return


    def verify_suppliers(self):
        """Mass verification of missing suppliers"""
        invalid_lines = self.requisition_line_ids.filtered(
            lambda l: not l.seller_id and not l.purchased_product
        )
        
        if invalid_lines:
            products = invalid_lines.mapped('product_id.display_name')
            raise ValidationError(
                "Products without assigned supplier:\n- %s" % 
                "\n- ".join(products)
            )

    def update_seller(self):
        """Massive supplier update optimized"""
        SellerInfo = self.env['product.supplierinfo'].sudo()
        suppliers_to_create = []
        
        valid_lines = self.requisition_line_ids.filtered(
            lambda l: l.seller_id and 
            l.seller_id not in l.product_id.seller_ids.partner_id and 
            len(l.product_id.seller_ids) <= 10
        )
        
        template_sequences = {
            tmpl.id: max(tmpl.seller_ids.mapped('sequence'), default=0)
            for tmpl in valid_lines.mapped('product_id.product_tmpl_id')
        }
        
        for line in valid_lines:
            tmpl_id = line.product_id.product_tmpl_id.id
            suppliers_to_create.append({
                'product_tmpl_id': tmpl_id,
                'partner_id': line.seller_id.id,
                'sequence': template_sequences[tmpl_id] + 1,
                'price': line.unit_cost,
                'company_id': self.company_id.id,
                'currency_id': self.company_id.currency_id.id,
                'min_qty': 0
            })
            template_sequences[tmpl_id] += 1
        
        if suppliers_to_create:
            SellerInfo.create(suppliers_to_create)

    def action_generate_budgets(self):
        for record in self:
            if record.state == 'approved':
                self.verify_suppliers()
                self.update_seller() 
                lines_sorted=sorted(record.requisition_line_ids.filtered(lambda l: l.purchased_product == False
                ), key=lambda r: r.seller_id.id)
                self.create_purchase(lines_sorted)
                self.write({
                    'state': 'budgeted'
                })
                record.requisition_line_ids.write({
                    'product_quota': True
                })

    def create_purchase(self, requisition_lines):  
        for key, group in groupby(requisition_lines , key=lambda r: r.seller_id):
            self.env['purchase.order'].create({
                                                'partner_id': key.id,
                                                'date_order': datetime.now(),
                                                'company_id': self.company_id.id,
                                                'requisition_id': self.id,
                                                'purchase_type_id': self.requisition_budgeting_id.purchase_type_id.id or False,
                                                'origin':self.name,
                                                'order_line':self.generate_lines_oc(list(group), key),
                                                'payment_term_id': key.property_payment_term_id.id or False,
                                            })
        return

    def generate_lines_oc(self, lines, partner=None):
        lis=[]
        for line in lines:
            product_lang = line.product_id.with_context(lang=line.seller_id.lang,partner_id=line.seller_id.id)
            taxes = line.mapped('product_id.supplier_taxes_id.id')
            observation=''
            if line.observation:
                observation = line.observation
            if line.observation_purchase:
                observation =  observation +' / ' if line.observation else observation + line.observation_purchase 
            seller = line.product_id.seller_ids.filtered(lambda x: x.partner_id == partner)[0]
            dct_lines = {
                        'product_id': line.product_id.id,
                        'product_qty': line.approved_quantity,
                        'price_unit': seller.price if seller else line.unit_cost,
                        'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'name': observation if observation else product_lang.display_name,
                        'product_uom': line.product_uom_id.id,
                        'taxes_id': [(6,0, taxes)]
                        }
            if line.approved_quantity > 0:
                lis.append((0,0,dct_lines))
        return lis        

    def get_mails(self):
        emails = False
        user_ids = self.requisition_budgeting_id.requisition_mail_ids.filtered(
            lambda x: x.state == self.state
        ).mapped('user_ids.login')
        if user_ids:
            emails = ";".join(user_ids)
        return emails
        
    def modified_products(self):
        extra_body = ""
        if self.requisition_status == 'Confirmed':
            for line in self.requisition_line_ids:
                if line.quantity != line.approved_quantity:
                    extra_body += f"Product: {line.name} - Quantity: {line.approved_quantity} <br>"
        return extra_body

    def send_mail(self):
        extra = self.modified_products()
        extra_body = f"Approved products with changes: <br><br>{extra}" if extra else ""
        mail_body = (
            f"For your information, requisition No. {self.name} has just been {self.requisition_status}.<br>"
            f"{extra_body}<br> "
            "For inquiries, please contact Systems."
        )
        mails_list = self.get_mails()
        if not mails_list:
            return
        mail_vals = {
            'email_from': self.company_id.requisition_mail or self.company_id.email,
            'email_to': mails_list,
            'subject': f"{self.company_id.name.upper()} REQUISITION Nº {self.name.upper()} OF TYPE {self.requisition_budgeting_id.name.upper()} HAS JUST BEEN {self.requisition_status.upper()}",
            'body_html': mail_body,
            'auto_delete': True,
        }
        mail = self.env['mail.mail'].create(mail_vals)
        self.env['mail.mail'].send(mail)


    @api.constrains('total_requisition')
    def exceed_quota(self):
        for record in self:
            if record.level != 'administrative':
                total = record.total_requisition
                if record.level == 'maintenance':
                    total = sum([line.sub_total_quotas for line in record.requisition_line_ids])   
                if total > record.budget:
                    raise ValidationError("The total of the requisition exceeds the established budget")

    def dmn_requisition(self):
        dmn=[   
            ('product_quota', '=', True),
            ('paid_quota', '>', 0),
            ('company_id', '=', self.company_id.id),
            ('requisition_budgeting_id', '=', self.requisition_budgeting_id.id),
            ('requisition_id.state','not in',['canceled']),
                ] 
        return dmn
    
    def _add_quotas_lines_onchange(self):          
        if self.is_quota:            
            requisition_line_ids = self.env['requisition.line'].search(self.dmn_requisition(), order="id desc")
            if requisition_line_ids:
                lista_data = []
                for line in requisition_line_ids:
                    dct = line.copy_data()[0]
                    dct['product_quota']=True
                    dct['paid_quota'] += 1
                    lista_data.append([0, 0, dct])
                self.requisition_line_ids = lista_data
        elif not self.is_quota:
            self.requisition_line_ids = [(6, 0, [])]

    def action_print(self):
        self.ensure_one()
        return self.env.ref(f'{self._module}.action_report_requisition').report_action(self)
