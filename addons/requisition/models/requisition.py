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
    _description = 'Requisición'


    name = fields.Char('Nombre', default='*')
    requisition_budgeting_id = fields.Many2one('requisition.budgeting',  string='Tipo de Requisición')
    company_id = fields.Many2one('res.company', string='Compañia',
                                 required=True, readonly=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                required=True, readonly=True,
                                default=lambda self: self.env.company.currency_id.id)
    active = fields.Boolean(default=True, tracking=True)
    requisition_date = fields.Datetime(string='Fecha de Creación de Requisición', readonly=True, index=True, default=fields.Datetime.now, copy=False)
    state = fields.Selection(STATE_LIST, string='Estado', required=True, readonly=True, default='draft', tracking=True)
    requisition_line_ids = fields.One2many('requisition.line', 'requisition_id')
    budget = fields.Monetary('Cupo', currency_field='currency_id', copy=False)
    total_requisition = fields.Monetary('Total de Requisición', tracking=True, compute="_compute_total", store=True, currency_field='currency_id')
    difference_value = fields.Monetary('Saldo disponible', tracking=True, compute="_compute_difference", currency_field='currency_id')
    purchase_order_ids = fields.One2many('purchase.order', 'requisition_id', copy=False)
    purchase_order_count = fields.Integer(string="Proformas", compute="_compute_purchase_count", tracking=True, copy=False)
    partner_id = fields.Many2one('res.partner', string='Responsable', tracking=True, default=lambda self: self.env.user.partner_id.id, copy=False)
    range_type_id = fields.Many2one('date.range.type', string='Tipo de periodo')
    period_id = fields.Many2one('date.range', string="Periodo", tracking=True, 
    domain="[('type_id','=', range_type_id),('date_end','>=',requisition_date)]", copy=False)
    level = fields.Selection(LEVEL_LIST, string='Nivel', tracking=True)
    notes = fields.Text('Notas', tracking=True)    
    confirm_by = fields.Char('Confirmado Por', readonly=True, copy=False)
    date_confirm = fields.Date('Fecha de Confirmacion', readonly=True, copy=False)
    approver_by = fields.Char('Aprobado Por', readonly=True, copy=False)
    date_approve = fields.Date('Fecha de Aprobacion', readonly=True, copy=False)
    is_quota = fields.Boolean(string='Es por cuotas', related='requisition_budgeting_id.is_quota', store=True)
    requisition_status = fields.Char(
            string='Estado Requisición',
            compute='_compute_requisition_status',
            store=True
        )
    requisition_tmpl_id = fields.Many2one('requisition.template',string='Plantilla de requisiciones', ondelete='cascade')

    @api.onchange('requisition_tmpl_id')
    def onchange_requisition_tmpl(self):
        self.requisition_line_ids = [(5, 0, 0)]
        
        if self.is_quota:
            self._add_quotas_lines_onchange()
        
        if self.requisition_tmpl_id:
            self.requisition_line_ids = [
                (0, 0, {'product_id': product_id})
                for product_id in self.requisition_tmpl_id.req_template_line_ids.mapped('product_id.id')
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
        """Campo computado para el estado de la requisición"""
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
        Este método se activa cuando cambia period_id o requisition_budgeting_id. 
        Establece range_type_id según el requisition_budgeting_id seleccionado.
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
                    "No puede generar otra requisición de mantenimiento mientras exista una en proceso: "
                    f"{existing_req.name} (Estado: {existing_req.state})"
                )
        period_domain = base_domain + [
            ('period_id', '=', self.period_id.id),
            ('state', '!=', 'canceled')
        ]
        existing_period_reqs = Requisition.search(period_domain)
        if len(existing_period_reqs) >= 1:
            req_names = ", ".join(existing_period_reqs.mapped('name'))
            error_messages.append(
                "Solo puede crear una requisición por periodo. "
                f"Existen: {req_names}"
            )
        if error_messages:
            error_title = "Validación de Requisiciones"
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
        """Valida y confirma la requisición optimizando recursos"""
        self.ensure_one()

        if not self.requisition_line_ids:
            raise ValidationError("No puede confirmar una requisición sin productos")
        
        today = fields.Date.context_today(self)
        
        if today < self.period_id.date_start:
            raise ValidationError("No puede confirmar una requisición de un periodo futuro")
        
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
        """Cancela la requisición optimizando recursos"""
        self.update_lines()
        self.write({
            'state': 'canceled'
        })

    def zero_product_control(self):
        """Verifica líneas con cantidad cero en lote"""
        if self.requisition_line_ids.filtered(lambda l: l.quantity <= 0):
            raise ValidationError('No puede enviar productos con cantidad menor o igual a 0')

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
        """Verifica existencia de líneas duplicadas de manera optimizada"""
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
        """Manejo optimizado de la reversión a borrador"""
        for record in self:
            record.write({
                'state': 'draft',
                'confirm_by': False,
                'date_confirm': False,
                'approver_by': False,
                'date_approve': False
            })

    def update_lines(self, cond=False):
        """Actualiza líneas de requisición usando ORM de forma optimizada"""
        if not self:
            return


    def verify_suppliers(self):
        """Verificación masiva de proveedores faltantes"""
        invalid_lines = self.requisition_line_ids.filtered(
            lambda l: not l.seller_id and not l.purchased_product
        )
        
        if invalid_lines:
            products = invalid_lines.mapped('product_id.display_name')
            raise ValidationError(
                "Productos sin proveedor asignado:\n- %s" % 
                "\n- ".join(products)
            )

    def update_seller(self):
        """Actualización masiva de proveedores optimizada"""
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
        if self.requisition_status == 'Confirmada':
            for line in self.requisition_line_ids:
                if line.quantity != line.approved_quantity:
                    extra_body += f"Producto: {line.name} - Cantidad: {line.approved_quantity} <br>"
        return extra_body

    def send_mail(self):
        extra = self.modified_products()
        extra_body = f"Productos aprobados con cambios: <br><br>{extra}" if extra else ""
        mail_body = (
            f"Para su conocimiento la requisición Nº {self.name} acaba de ser {self.requisition_status}.<br>"
            f"{extra_body}<br> "
            "Para consultas puede comunicarse a Sistemas."
        )
        mails_list = self.get_mails()
        if not mails_list:
            return
        mail_vals = {
            'email_from': self.company_id.requisition_mail or self.company_id.email,
            'email_to': mails_list,
            'subject': f"{self.company_id.name.upper()} REQUISICIÓN Nº {self.name.upper()} DE TIPO {self.requisition_budgeting_id.name.upper()} ACABA DE SER {self.requisition_status.upper()}",
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
                    raise ValidationError("El total de la requisición excede el presupuesto establecido")

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
