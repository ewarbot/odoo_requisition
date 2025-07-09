# -*- coding: utf-8 -*-
from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'
    _description = 'Requisition Company'

    requisition_mail = fields.Char('Email Requisition', help="Correo electrónico para recibir las requisiciones de compra")