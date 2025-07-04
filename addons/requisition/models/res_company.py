# -*- coding: utf-8 -*-
from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'
    _description = 'Compañia Requisición'

    requisition_mail = fields.Char('Correo Requisición', help="Correo electrónico para recibir las requisiciones de compra")