STATE_LIST = [
    ('draft', 'Borrador'), 
    ('rejected', 'Rechazada'),
    ('confirmed', 'Confirmado'),
    ('approved', 'Aprobado'),
    ('budgeted', 'Proforma'),
    ('canceled', 'Anulado')
    ]

LEVEL_LIST = [
        ('general', 'General'),
        ('administrative', 'Administrativa'), 
        ('maintenance', 'Mantenimiento')
    ]

STATE_TO_STATUS = {
        'draft': 'Creada',
        'rejected': 'Rechazada',
        'confirmed': 'Confirmada',
        'approved': 'Aprobada',
        'budgeted': 'Enviada a Proforma',
        'canceled': 'Anulada'
    }
