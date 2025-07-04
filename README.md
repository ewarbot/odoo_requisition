<h1>📦 Odoo 18 Community - odoo_requisition</h1>

<p>Este repositorio es un template para un proyecto Odoo 18 Community.</p>
<p>La estructura incluye todo lo necesario para un ciclo completo de desarrollo, pruebas, integración continua y despliegue. Compatible con entornos Docker</p>

<h2>🗂️ Estructura del Proyecto</h2>

<pre>
.
├── .config/                     # Archivos de configuración inicial
│   ├── entrypoint.sh            # Script de arranque del contenedor
│   ├── odoo.conf                # Ajustes de Odoo
│   ├── requirements.txt         # Dependencias Python
│   └── wait-for-psql.py         # Espera a que PostgreSQL esté listo
│
├── addons/                               # Módulos personalizados
│
├── docker-compose.yml           # Configuración Docker Compose para desarrollo
├── Dockerfile                   # Imagen base para el contenedor Odoo
├── .gitignore
└── README.md
</pre>

  <h2>🛠️ Requisitos</h2>
  <table border="1" cellpadding="6" cellspacing="0">
    <thead>
      <tr>
        <th>Herramienta</th>
        <th>Uso</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Docker & Docker Compose</strong></td>
        <td>Orquestación de contenedores</td>
      </tr>
      <tr>
        <td><strong>Git</strong></td>
        <td>Control de versiones</td>
      </tr>
      <tr>
        <td><strong>Visual Studio Code</strong></td>
        <td>IDE recomendado (con extensión “Remote – Containers”)</td>
      </tr>
    </tbody>
  </table>
  <hr/>

  <h2>🧰 Configuración de Odoo</h2>
  <p>En <code>.config/odoo.conf</code> tienes los parámetros mínimos recomendados para desarrollo:</p>
  <pre><code>[options]
addons_path = /mnt/extra-addons
db_host     = db
db_port     = 5432
db_user     = odoo
db_password = odoo
log_level   = info
</code></pre>
  <hr/>

  <h2>🐍 Dependencias Python</h2>
  <table border="1" cellpadding="6" cellspacing="0">
    <thead>
      <tr>
        <th>Librería</th>
        <th>Versión</th>
        <th>Descripción</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>paramiko</strong></td>
        <td>3.2.0</td>
        <td>Conexiones SSH</td>
      </tr>
      <tr>
        <td><strong>cryptography</strong></td>
        <td>41.0.0</td>
        <td>Funciones de cifrado</td>
      </tr>
      <tr>
        <td><strong>xades</strong></td>
        <td>0.2.4</td>
        <td>Firmas electrónicas (XAdES)</td>
      </tr>
      <tr>
        <td><strong>xmlsig</strong></td>
        <td>0.1.9</td>
        <td>Firmas XML</td>
      </tr>
      <tr>
        <td><strong>rlpycairo</strong></td>
        <td>–</td>
        <td>Generación de gráficos en Python</td>
      </tr>
      <tr>
        <td><strong>phonenumbers</strong></td>
        <td>–</td>
        <td>Validación y formateo de teléfonos</td>
      </tr>
      <tr>
        <td><strong>pyOpenSSL</strong></td>
        <td>24.0.0</td>
        <td>Cifrado de conexiones TLS/SSL</td>
      </tr>
      <tr>
        <td><strong>zeep</strong></td>
        <td>–</td>
        <td>Cliente SOAP</td>
      </tr>
      <tr>
        <td><strong>pandas</strong></td>
        <td>2.0.3</td>
        <td>Análisis y manipulación de datos</td>
      </tr>
    </tbody>
  </table>
  <p><strong>Nota:</strong> Ajusta las versiones según tus necesidades y compatibilidad con Odoo 18.</p>
  <hr/>

  <h2>🐋 Docker & Docker Compose</h2>
  <p>En <code>docker-compose.yml</code> definimos al menos dos servicios:</p>
  <ul>
    <li><strong>db</strong>: PostgreSQL</li>
    <li><strong>odoo</strong>: Odoo 18 con tu <code>Dockerfile</code></li>
  </ul>
  <p>El <code>entrypoint.sh</code> de <code>.config/</code> se encarga de:</p>
  <ul>
    <li>Ejecutar <code>wait-for-psql.py</code> para asegurarse de que PostgreSQL esté arriba</li>
    <li>Llamar a <code>odoo-bin</code> con la configuración de <code>.config/odoo.conf</code></li>
  </ul>
  <hr/>

  <h2>⚙️ Scripts de Arranque</h2>

  <h3>entrypoint.sh (en .config/)</h3>
  <pre><code>#!/usr/bin/env bash
set -e
python3 /mnt/extra-addons/.config/wait-for-psql.py --host db --port 5432
exec odoo-bin --config=/mnt/extra-addons/.config/odoo.conf "$@"
</code></pre>

  <h3>wait-for-psql.py (en .config/)</h3>
  <p>Pequeño script en Python que espera hasta que el puerto PostgreSQL acepte conexiones.</p>
  <hr/>

  <h2>💻 Comandos Útiles</h2>

  <h3>Login a GitHub Container Registry</h3>
  <pre><code>echo "&lt;TU_GITHUB_TOKEN&gt;" | docker login ghcr.io -u &lt;TU_USUARIO_GITHUB&gt; --password-stdin</code></pre>

  <h3>Levantar en modo desarrollo</h3>
  <pre><code>docker-compose up --build</code></pre>

  <h3>Instalar dependencias locales (sin Docker)</h3>
  <pre><code>pip install -r .config/requirements.txt</code></pre>
  <hr/>

  <p>¡Listo! Con esta plantilla tendrás un entorno reproducible y listo para desarrollar tus propios módulos en Odoo 18 Community.</p>

</body>
</html>
