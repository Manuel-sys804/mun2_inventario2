# MUN-2 · Sistema de Inventario

App web de inventario y ventas para tienda de ropa, pensada para que
**varios empleados la usen desde distintas computadoras** conectadas
a la misma red (WiFi/router de la tienda), todos viendo y actualizando
el mismo inventario en tiempo real.

## Cómo funciona

Una sola computadora actúa como **servidor** (guarda la base de datos
`inventario.db`). Las demás computadoras solo necesitan un navegador
y se conectan a la IP de esa computadora. No hay que instalar nada
en las computadoras de los empleados, solo en la del servidor.

```
[PC Admin - Servidor]  <--- WiFi/Red local --->  [PC Vendedor 1]
     inventario.db                                [PC Vendedor 2]
     (corre app.py)                                [Tablet / Celular]
```

## 1. Instalación (solo en la computadora servidor)

Necesitas Python 3.9 o más reciente instalado.

```bash
# 1. Entra a la carpeta del proyecto
cd mun2_inventario

# 2. (Recomendado) crea un entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# 3. Instala las dependencias
pip install -r requirements.txt

# 4. Inicializa la base de datos con los productos y usuarios de ejemplo
python database.py

# 5. Arranca el servidor
python app.py
```

Verás algo como:

```
* Running on http://0.0.0.0:5000
```

## 2. Encontrar la IP de la computadora servidor

En esa misma computadora, abre otra terminal y ejecuta:

- **Windows:** `ipconfig` → busca "Dirección IPv4" (ej. `192.168.1.45`)
- **Mac:** `ipconfig getifaddr en0`
- **Linux:** `hostname -I`

## 3. Conectar los demás empleados

Desde cualquier otra computadora, celular o tablet **conectada al
mismo WiFi**, abre el navegador y entra a:

```
http://192.168.1.45:5000
```

(reemplaza la IP por la que obtuviste en el paso 2). Puedes guardar
esa dirección como favorito en cada dispositivo para no escribirla
cada vez.

> ⚠️ La computadora servidor debe permanecer encendida y con `python
> app.py` corriendo mientras los empleados la usan. Si la apagas,
> nadie más podrá acceder mientras tanto.

## 4. Usuarios iniciales

| Usuario | Contraseña | Rol            |
|---------|-----------|----------------|
| admin   | admin123  | Administrador  |
| carlos  | 123456    | Vendedor       |
| sofia   | 123456    | Vendedor       |

**Cambia estas contraseñas** desde la sección "Empleados" (creando
usuarios nuevos) tan pronto pongas el sistema en marcha — considera
desactivar o eliminar los usuarios de ejemplo que no vayas a usar.

## 5. Secciones del sistema

- **Dashboard:** ventas del día/mes, alertas de stock bajo, pedidos
  por entregar y (para admin) facturas pendientes de pago.
- **Inventario:** buscar, filtrar, y (admin) crear/editar/eliminar
  productos y ajustar stock.
- **Ventas:** registrar una venta indicando el método de pago
  (Efectivo, Tarjeta, Transferencia o Pago móvil); descuenta stock
  automáticamente.
- **Pedidos:** encargos de clientes que aún no se entregan. Cada uno
  tiene un estado — **Pendiente → Enviado → Entregado** (o Cancelado)
  — que se actualiza con un clic.
- **Facturación** (solo admin): registra facturas de compra a
  proveedores (mercancía, empaque, transporte, etc.) marcadas como
  Pagada o Pendiente, con totales por proveedor y por mes.
- **Reportes** (solo admin): valor y costo del inventario, ganancia
  potencial, gasto facturado en mercancía, y ganancia real
  (ventas históricas − gastos facturados).
- **Empleados** (solo admin): crear/activar/desactivar cuentas.
- **Mi perfil:** cualquier usuario ve su propio resumen de actividad
  y puede cambiar su contraseña.

## 6. Permisos por rol

- **Vendedor:** ve el inventario, registra ventas y pedidos de
  clientes, y gestiona su propio perfil.
- **Administrador:** todo lo anterior, más edición de inventario,
  facturación, reportes financieros y gestión de empleados.

## 6. Respaldo de datos

Todo se guarda en un solo archivo: `inventario.db` (en la carpeta del
proyecto, en la computadora servidor). Para respaldar el negocio,
simplemente copia ese archivo a una USB o a la nube de vez en cuando.

## 7. Dejar el servidor corriendo todo el día (opcional)

Si quieres que el sistema esté disponible sin tener la terminal
abierta, puedes:
- **Windows:** usar el Programador de tareas para ejecutar
  `python app.py` al iniciar sesión.
- **Mac/Linux:** usar `nohup python app.py &` o configurar un
  servicio con `systemd`/`launchd`.

## 8. Notas técnicas

- Base de datos: SQLite (`inventario.db`), no requiere servidor de
  base de datos aparte.
- Framework: Flask.
- Las contraseñas se guardan con hash seguro (no en texto plano).
- Para producción real (muchos usuarios simultáneos, acceso por
  internet en vez de red local), se recomienda migrar a un hosting
  con HTTPS y considerar PostgreSQL en vez de SQLite.
