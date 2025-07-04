# -*- coding: utf-8 -*-
from odoo import models, fields, api, _ 
from odoo.exceptions import ValidationError
from .data import STATE_LIST


class RequisitionMail(models.Model):
    _name = 'requisition.mail'
    _description = 'Configuración de correo requisiciones'
    _order = "id,sequence"

    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=1)
    name = fields.Char(string='Nombre')
    budgeting_id = fields.Many2one('requisition.budgeting')
    state = fields.Selection(STATE_LIST)
    user_ids = fields.Many2many('res.users', string='Usuarios')
