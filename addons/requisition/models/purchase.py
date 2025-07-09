# -*- coding: utf-8 -*-
from odoo import models, fields, api, _ 
from odoo.exceptions import ValidationError
import logging

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    _description = 'Purchase Order Requisition'

    requisition_id = fields.Many2one(comodel_name='requisition', ondelete='cascade')
    purchase_type_id = fields.Many2one('purchase.type', string='Purchase Type', ondelete='cascade')