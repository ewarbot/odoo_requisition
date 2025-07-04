from odoo import api, fields, models
from datetime import datetime

class DateRange(models.Model):
    _inherit = "date.range"
    _description = "Rango de Fechas Requisición"
    _rec_name = 'description'

    description = fields.Char(compute='_compute_period_description', string="Periodo")

    @api.depends('date_start', 'date_end')
    def _compute_period_description(self):
        """Cálculo optimizado de la descripción del periodo"""
        date_format = '%d/%m/%Y'
        for record in self:
            if record.date_start and record.date_end:
                start = fields.Date.from_string(record.date_start).strftime(date_format)
                end = fields.Date.from_string(record.date_end).strftime(date_format)
                record.description = f"{start} - {end}"
            else:
                record.description = "Periodo no definido"
