# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _
from odoo.exceptions import ValidationError

class PurchaseType(models.Model):
    _name = "purchase.type"
    _inherit = ['mail.thread']
    _order = 'sequence,name,id'
    _description = "Tipo de compra"

    name = fields.Char(string='Nombre', required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    sequence = fields.Integer('Secuencia', default=10)
    