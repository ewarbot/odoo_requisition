STATE_LIST = [
    ('draft', 'Draft'), 
    ('rejected', 'Rejected'),
    ('confirmed', 'Confirmed'),
    ('approved', 'Approved'),
    ('budgeted', 'Budgeted'),
    ('canceled', 'Canceled')
    ]

LEVEL_LIST = [
        ('general', 'General'),
        ('administrative', 'Administrative'),
        ('maintenance', 'Maintenance')
    ]

STATE_TO_STATUS = {
        'draft': 'Created',
        'rejected': 'Rejected',
        'confirmed': 'Confirmed',
        'approved': 'Approved',
        'budgeted': 'Sent to Proforma',
        'canceled': 'Canceled'
    }
