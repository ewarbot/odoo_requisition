## 1. Visión General

El módulo **requisition** añade funcionalidad de gestión de requisiciones de compras (solicitudes internas), integrándose con Odoo Purchase y Stock. Permite definir presupuestos, plantillas, líneas de requisición, generación de órdenes de compra y notificaciones por correo.

## 2. Estructura de Carpetas

```
requisition/
├── __init__.py                # Inicialización del paquete
├── __manifest__.py            # Metadatos y dependencias
├── controller/                # Controladores HTTP para endpoints personalizados
│   └── __init__.py
├── data/                      # Datos de referencia y plantillas de correo
│   ├── purchase_type_data.xml
│   └── requisition_email.xml
├── models/                    # Definición de modelos y lógica de negocio
│   ├── __init__.py
│   ├── data.py                # Constantes de estado, niveles y mapeos
│   ├── date_range.py          # Extiende date.range con descripción de periodo
│   ├── purchase_type.py       # Modelo purchase.type
│   ├── purchase.py            # Extensión de purchase.order para vinculación de requisiciones
│   ├── requisition_budgeting.py  # Presupuestos y líneas de presupuesto
│   ├── requisition_line.py    # Líneas de requisición con lógica de cotas y validaciones
│   ├── requisition_mail.py    # Configuración de envíos de correo según estado
│   ├── requisition_template.py# Plantillas de requisición reutilizables
│   ├── requisition.py         # Modelo principal requisition con workflow completo
│   └── res_company.py         # Extensión de res.company para correo de requisición
├── report/                    # Definición de formato y plantilla QWeb PDF
│   ├── paper_format.xml
│   └── report_requisition.xml
├── security/                  # Definición de grupos, reglas y accesos
│   ├── ir.model.access.csv
│   └── requisition_security.xml
├── views/                     # Vistas XML: menú, búsquedas, listas y formularios
│   ├── menu_views.xml
│   ├── purchase_type_views.xml
│   ├── purchase_views.xml
│   ├── requisition_budgeting_views.xml
│   ├── requisition_template_views.xml
│   ├── requisition_line_views.xml
│   └── requisition_views.xml
├── wizard/                    # Asistente (wizard) para operaciones específicas
│   └── __init__.py            # (vacío o se incorporan wizards menores)
└── static/description/        # Iconografía y descripción estática
    └── icon.png
```

## 3. Dependencias

* **purchase:** Para generar y vincular purchase.order.
* **stock:** Para gestionar inventarios si se requiere.
* **date\_range:** Para definir rangos de fechas en presupuestos y períodos.

## 4. Controladores

* Carpeta `controller/`: preparada para exponer endpoints HTTP (no se incluyen controladores adicionales por defecto).

## 5. Datos de Referencia

* **purchase\_type\_data.xml:** carga tipos de orden de compra iniciales.
* **requisition\_email.xml:** plantilla de correo genérica para notificaciones.

## 6. Modelos

### 6.1 data.py

* Define constantes:

  * `STATE_LIST`: estados de la requisición.
  * `LEVEL_LIST`: niveles de requisición.
  * `STATE_TO_STATUS`: mapea estados a textos legibles.

### 6.2 date\_range.py

* Hereda `date.range`, agrega campo calculado `description` con formato `DD/MM/YYYY - DD/MM/YYYY`.

### 6.3 purchase\_type.py

* Modelo `purchase.type`: nombre, secuencia y flags de activo, con tracking.

### 6.4 purchase.py

* Extiende `purchase.order` añadiendo `requisition_id` y `purchase_type_id` para vincular con requisición.

### 6.5 requisition\_budgeting.py

* Modelo `requisition.budgeting`: presupuesto por tipo, control de cuotas, secuencia para generar nombres de requisición.
* Modelo `requisition.budgeting.line`: líneas de presupuesto vinculadas a producto o categoría.

### 6.6 requisition\_line.py

* Modelo `requisition.line`: línea de una requisición.
* Lógica de computación de dominio de productos, validaciones de cantidades, cálculo de subtotales y cuotas.
* Métodos para normalizar precios con impuestos incluidos y conversión de unidades.

### 6.7 requisition\_mail.py

* Modelo `requisition.mail`: define usuarios y estados para envío de notificaciones automáticas.

### 6.8 requisition\_template.py

* Modelo `requisition.template` y `requisition.template.line`: plantillas predefinidas de líneas de requisición basadas en presupuestos.

### 6.9 requisition.py

* Modelo principal `requisition` con campos: nombre, presupuesto, totales, estado, workflow (confirmar, aprobar, cancelar, generar presupuestos).
* Métodos: validaciones de flujo, generación de órdenes de compra por proveedor, envío de correos, impresión de reportes.

### 6.10 res\_company.py

* Añade campo `requisition_mail` en compañía para definir correo emisor de requisiciones.

## 7. Vistas

* **Listas (`<list>`):** listado de requisiciones, líneas, presupuestos, tipos de compra y plantillas.
* **Formularios (`<form>`):** edición de todos los modelos con botones de acción en header y statusbar.
* **Search:** vistas de búsqueda para filtrar por campos clave.
* **Menú:** menú principal `Requisiciones` con submenús para estados y configuración.

## 8. Seguridad

* Grupos: Revisores, Digitador, Biólogos, Aprobadores, Administrador, con herencia jerárquica.
* `ir.model.access.csv`: define permisos CRUD para cada modelo.
* `requisition_security.xml`: asigna grupos a menús y acciones.

## 9. Reportes

* **paper\_format.xml:** configura tamaño y márgenes para PDF.
* **report\_requisition.xml:** plantilla QWeb PDF con diseño de cabecera, tabla de líneas agrupadas por categoría, totales y pie de resumen.

## 10. Manifest (`__manifest__.py`)

* Metadatos: nombre, autor, versión, licencia.
* Dependencias: `purchase`, `stock`, `date_range`.
* Orden de carga: seguridad, datos, vistas, reportes.
* `application: True` para aparecer en Apps.
