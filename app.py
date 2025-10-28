from flask import Flask, render_template, request, redirect, url_for, flash, session

from flask_mysqldb import MySQL
import MySQLdb.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

import secrets
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

def generar_token(email):
    token = secrets.token_urlsafe(32)
    expiry = datetime.now() + timedelta (hours=1)
    cur = mysql.connection.cursor()
    cur.execute("UPDATE usuarios SET reset_token= %s, token_expiry = %s WHERE username = %s", (token, expiry,email))
    mysql.connection.commit()
    cur.close()
    return token

def enviar_correo_reset(email,token):
    enlace = url_for('reset', token = token,_external=True)
    cuerpo = f"""Hola, Solicitaste recuperar tu contraseña. Haz click en el siguiente enlace:
    {enlace}
    Este enlace expirará en 1 hora.
    Si no lo solicitaste, ignora este mensaje. """
    
    remitente = 'yanfristib@gmail.com'
    clave = 'jkud ywjs kvnk thia'
    mensaje = MIMEText(cuerpo)
    mensaje['subject'] = 'Recuperar contraseña'
    mensaje['From'] = 'yanfristib@gmail.com'
    mensaje['To'] = email

    server = smtplib.SMTP('smtp.gmail.com',587)
    server.starttls()
    server.login(remitente,clave)
    server.sendmail(remitente,email,mensaje.as_string())
    server.quit()

def enviar_correo_factura(email, factura_data):
    # Construir la lista de productos con detalles del viaje
    productos_lista = ""
    for producto in factura_data['productos']:
        productos_lista += f"    • {producto['nombre']} - ${producto['precio']}\n"
        
        # Agregar detalles del viaje si existen
        if 'detalles_viaje' in producto:
            detalles = producto['detalles_viaje']
            productos_lista += f"      📅 Fechas: {detalles.get('fecha_salida', 'No especificada')} al {detalles.get('fecha_regreso', 'No especificada')}\n"
            productos_lista += f"      👥 Pasajeros: {detalles.get('adultos', '1')} adultos, {detalles.get('ninos', '0')} niños\n"
            productos_lista += f"      ✈️ Tipo: {detalles.get('tipo_viaje', 'No especificado')} - Clase: {detalles.get('clase', 'No especificada')}\n"
            productos_lista += f"      📞 Contacto: {detalles.get('telefono', 'No especificado')}\n"
            productos_lista += f"      📧 Email: {detalles.get('email', 'No especificado')}\n"
            if detalles.get('comentarios'):
                productos_lista += f"      💬 Comentarios: {detalles['comentarios']}\n"
        productos_lista += "\n"

    cuerpo = f"""
    ✈️ Airsoft - Confirmación de Compra
    
    ¡Hola!
    
    Tu compra en nuestro catálogo ha sido procesada exitosamente. 
    
    📋 **DETALLES DE LA COMPRA:**
    Número de Factura: #{factura_data['numero_factura']}
    Fecha: {factura_data['fecha']}
    Total: ${factura_data['total']}
    Método de Pago: {factura_data['metodo_pago']}
    
    🛒 **PRODUCTOS COMPRADOS:**
{productos_lista}
    📧 **CONTACTO:**
    Para cualquier consulta sobre tu compra, contáctanos en: yanfristib@gmail.com
    
    ¡Gracias por comprar en Airsoft!
    Te esperamos en tu próxima aventura ✈️
    """
    
    remitente = 'yanfristib@gmail.com'
    clave = 'jkud ywjs kvnk thia'
    mensaje = MIMEText(cuerpo)
    mensaje['Subject'] = f'✅ Confirmación de Compra - Factura #{factura_data["numero_factura"]}'
    mensaje['From'] = 'yanfristib@gmail.com'
    mensaje['To'] = email

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, clave)
        server.sendmail(remitente, email, mensaje.as_string())
        server.quit()
        print(f"✅ Email de factura enviado a: {email}")
        return True
    except Exception as e:
        print(f"❌ Error enviando email de factura a {email}: {str(e)}")
        return False
    
def enviar_correo_reserva(email, reserva_data):
    """Envía email de confirmación de reserva similar al de forgot"""
    cuerpo = f"""
    ✈️ Airsoft  - Confirmación de Reserva
    
    ¡Hola {reserva_data['nombre_completo']}!
    
    Tu reserva ha sido confirmada exitosamente. Aquí los detalles:
    
    📋 Número de Reserva: #{reserva_data['id_reserva']}
    🏝️ Destino: {reserva_data['destino']}
    📅 Fechas: {reserva_data['fecha_salida']} al {reserva_data['fecha_regreso']}
    👥 Pasajeros: {reserva_data['adultos']} adultos, {reserva_data['ninos']} niños
    ✈️ Tipo de Viaje: {reserva_data['tipo_viaje']}
    💺 Clase: {reserva_data['clase']}
    💰 Precio Total: ${reserva_data['precio_total']}
    📞 Tus datos de contacto:
    Email: {email}
    Teléfono: {reserva_data['telefono']}
    
    📧 Para cualquier consulta, contáctanos en: yanfristib@gmail.com
    
    ¡Te contactaremos pronto con más detalles!
    """
    
    remitente = 'yanfristib@gmail.com'
    clave = 'jkud ywjs kvnk thia'
    mensaje = MIMEText(cuerpo)
    mensaje['Subject'] = f'✅ Confirmación de Reserva #{reserva_data["id_reserva"]}'
    mensaje['From'] = 'yanfristib@gmail.com'
    mensaje['To'] = email

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, clave)
        server.sendmail(remitente, email, mensaje.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error enviando email de reserva: {str(e)}")
        return False
app = Flask(__name__)
app.secret_key = 'clave_secreta'
app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER']='root'
app.config['MYSQL_PASSWORD']=''
app.config['MYSQL_DB']='airsoft'

mysql =MySQL(app)

@app.route('/')
def index():
    return render_template('index.html', current_page='index')


@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method =='POST':
        username = request.form['username']
        password_ingresada = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("""
        SELECT u.idUsuario, u.nombre, u.password, r.nombreRol
        FROM usuarios u
        JOIN usuario_rol ur ON u.idUsuario= ur.idUsuario
        JOIN roles r ON ur.idRol = r.idRol
        WHERE u.username =%s
        """, (username,))
        
        usuario = cur.fetchone()
        
        if usuario and check_password_hash (usuario [2], password_ingresada):
           session ['usuario'] = usuario[1]
           session ['rol'] = usuario[3]
           session ['idUsuario'] = usuario[0]  
           flash (f" | Bienvenido {usuario [1]}!")

           cur.execute("""
            INSERT INTO registro_login (idUsuario, fecha)
            VALUES (%s, NOW())
            """,(usuario[0],))
           mysql.connection.commit()
           cur.close()

           if usuario[3] == 'Admin':
              return redirect(url_for('dashboard'))
           elif usuario[3] == 'Usuario':
               return redirect(url_for('catalogo'))
           else:
               flash("Rol no reconocido")
               return redirect(url_for('login'))
        else:
           flash("Usuario o contraseña incorrecta")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada correctamente")
    return redirect(url_for('login'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form ['nombre']
        apellido = request.form ['apellido']
        username = request.form ['username']
        password = request.form ['password']
        hash = generate_password_hash (password)

        cur = mysql.connection.cursor ()
        try: 
            cur.execute("""INSERT INTO usuarios(nombre, apellido, username, password) VALUES (%s, %s, %s, %s) 
                        """, (nombre, apellido, username, hash))
            mysql.connection.commit()
            
            cur.execute("SELECT idUsuario FROM usuarios WHERE username =%s", (username,))
            nuevo_usuario = cur.fetchone()
            
            cur.execute("INSERT INTO usuario_rol(idUsuario, idRol) VALUES (%s, %s)", (nuevo_usuario[0], 2))
            mysql.connection.commit()
            
            
            session ['usuario'] = nombre
            session ['rol'] = 'Usuario'
            session ['idUsuario'] = nuevo_usuario[0]  
            
            flash ("Usuario registrado con exito")            
            return redirect(url_for('catalogo'))
        except:
            flash("Este correo ya esta registrado")
        finally:
            cur.close()        

    return render_template('registro.html')

@app.route('/forgot',methods=['GET','POST'])
def forgot():
    if request.method =='POST':
       email = request.form['email']
       
       cur = mysql.connection.cursor()
       cur.execute("SELECT idUsuario FROM usuarios WHERE username = %s", (email,))
       existe = cur.fetchone()
       cur.close()

       if not existe:
           flash("Este correo no está registrado.")
           return redirect(url_for('forgot'))


       token = generar_token(email)
       enviar_correo_reset(email, token) 

       flash ("Te enviamos un correo con el enlace para restablecer tu contraseña")
       return redirect(url_for('login'))
    return render_template('forgot.html')
    
@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset (token):
    cur = mysql.connection.cursor()
    cur.execute("SELECT idUsuario, token_expiry FROM usuarios WHERE reset_token = %s", (token,))
    usuario = cur.fetchone()
    cur.close()

    if not usuario or datetime.now() >usuario [1]:
       flash ("Token inválido o expirado.")
       return redirect(url_for('forgot'))
    if request.method == 'POST':
        nuevo_password = request.form ['password']
        hash_nueva = generate_password_hash (nuevo_password)

        cur = mysql.connection.cursor()
        cur.execute("UPDATE  usuarios SET password=%s, reset_token=NULL, token_expiry=NULL WHERE idUsuario=%s", (hash_nueva, usuario[0]))
        mysql.connection.commit()
        cur.close()

        flash ("Tu contraseña ha sido actualizada.")
        return redirect(url_for('login'))
    return render_template('reset.html')



@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        flash("Debes iniciar sesión para acceder al dashboard.")
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
         SELECT u.idUsuario, u.nombre, u.apellido, u.username, r.nombreRol, ur.idRol
         FROM usuarios u
         LEFT JOIN usuario_rol ur ON u.idUsuario = ur.idUsuario
         LEFT JOIN roles r ON ur.idRol = r.idRol          
         """)
    usuarios = cursor.fetchall()
    cursor.close()
    return render_template('dashboard.html', usuarios=usuarios)


@app.route('/actualizar/<int:id>', methods=['POST'])
def actualizar (id):
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    correo = request.form['correo']
    rol = request.form['rol']


    cursor = mysql.connection.cursor()
    cursor.execute("""UPDATE usuarios SET nombre=%s,apellido =%s, username=%s WHERE idUsuario=%s """,(nombre,apellido,correo,id))
    cursor.execute("SELECT * FROM usuario_rol WHERE idUsuario =%s", (id,))
    existe = cursor.fetchone()
    
    if existe:
        cursor.execute("UPDATE usuario_rol SET idRol =%s WHERE idUsuario=%s", (rol,id))
    else:
        cursor.execute("INSERT INTO usuario_rol(idUsuario, idRol) VALUES (%s, %s)", (id,rol))
    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('dashboard'))

@app.route('/eliminar/<int:id>')
def eliminar(id):
    cursor = mysql.connection.cursor()
    cursor.execute('DELETE FROM usuarios WHERE idUsuario=%s',(id,))
    mysql.connection.commit()
    cursor.close()
    flash ('Usuario eliminado')
    return redirect(url_for('dashboard'))

@app.route('/inventario')
def inventario():
    if 'rol' not in session or session['rol'] != 'Admin':
       flash("Acceso restringido solo para los administradores")
       return redirect(url_for('login'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()
    cursor.close()
    return render_template('inventario.html', productos=productos)    

@app.route('/agregar_producto', methods=['GET', 'POST'])
def agregar_producto():
    if 'rol' not in session or session['rol'] !='Admin':
        flash("Acceso restringido solo para los administradores")
        return redirect(url_for('login'))
    
    if request.method =='POST':
       nombre = request.form['nombre']
       descripcion = request.form['descripcion']
       precio = request.form['precio']
       cantidad = request.form['cantidad']
       imagen = request.files['imagen']
       
       filename = secure_filename(imagen.filename)
       imagen.save(os.path.join('static/uploads', filename))
       
       cursor = mysql.connection.cursor()
 
       cursor.execute("""
          INSERT INTO productos (nombre_producto, descripcion, precio, cantidad, imagen)
          VALUES (%s, %s, %s, %s, %s)
       """, (nombre, descripcion, precio, cantidad, filename))
       
       mysql.connection.commit()
       cursor.close()
       
       flash("Producto agregado correctamente")
       return redirect(url_for('inventario'))
    
    return render_template('agregar_producto.html')
@app.route('/eliminarProducto/<int:id>')
def eliminarProducto(id):
    cursor = mysql.connection.cursor()
    cursor.execute('DELETE FROM productos WHERE idProducto=%s',(id,))
    mysql.connection.commit()
    cursor.close()
    flash ('Producto eliminado')
    return redirect(url_for('inventario'))

@app.route('/actualizarProducto/<int:id>', methods=['POST'])
def actualizarProducto(id):
    nombre = request.form['nombre']
    precio = request.form['precio']
    descripcion = request.form['descripcion']
    cantidad = request.form['cantidad']
    imagen = request.files['imagen']
    cursor = mysql.connection.cursor()

    if imagen and imagen.filename != '':
        filename = secure_filename(imagen.filename)
        imagen.save(os.path.join('static/uploads', filename))

        cursor.execute("""
          UPDATE productos SET nombre_producto = %s,
                             precio = %s,
                             descripcion = %s,
                             cantidad = %s,
                             imagen = %s
                          WHERE idProducto = %s
                       """,(nombre, precio, descripcion, cantidad, filename, id))
    else:
        cursor.execute("""
          UPDATE productos SET nombre_producto = %s,
                             precio = %s,
                             descripcion = %s,
                             cantidad = %s
                          WHERE idProducto = %s
                       """,(nombre, precio, descripcion, cantidad, id)) 
        
    mysql.connection.commit()
    cursor.close()

    flash("Producto actualizado correctamente")
    return redirect(url_for('inventario'))

    
@app.route('/catalogo', methods=['GET','POST'])
def catalogo():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()
    resultados=[]
    if request.method == "POST":
        valor = request.form["busqueda"]
        cursor.execute("SELECT * FROM productos  WHERE nombre_producto LIKE %s", (f"%{valor}%",))
        resultados = cursor.fetchall()
    return render_template("catalogo.html", productos=productos,resultados=resultados)

@app.route('/agregar', methods=["GET", "POST"])
def agregar():
    if request.method == "POST":
        nombre = request.form['nombre']
        precio = request.form['precio']
        imagen = request.files['imagen']

        if imagen:
            filename = secure_filename(imagen.filename)
            imagen.save(os.path.join('static/uploads', filename))
            cursor = mysql.connection.cursor()
            
           
            cursor.execute("INSERT INTO productos (nombre_producto, precio, imagen) VALUES (%s, %s, %s)",
                           (nombre, precio, filename))
            
            mysql.connection.commit()  
            cursor.close()
            flash("Producto agregado con éxito")
            return redirect(url_for('catalogo'))   

    return render_template("agregar.html")

@app.route('/agregar2', methods=["GET", "POST"])
def productos():
    if request.method == "POST":
        nombre = request.form['nombre']
        precio = request.form['precio']
        descripcion = request.form['descripcion']
        cantidad = request.form['cantidad']
        imagen = request.files['imagen']
        categoria = request.form['categoria']
        proveedor = request.form['proveedor']
        
        if imagen:
            filename = secure_filename(imagen.filename)
            imagen.save(os.path.join('static/uploads', filename))
            cursor = mysql.connection.cursor()
            
     
            cursor.execute("INSERT INTO productos (nombre_producto, descripcion, precio, cantidad, imagen, id_categoria, id_proveedor) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                           (nombre, descripcion, precio, cantidad, filename, categoria, proveedor))
            
            mysql.connection.commit()  
            cursor.close()
            flash("Producto agregado con éxito")
            return redirect(url_for('catalogo'))  

    return render_template("productos.html")

@app.route('/carrito/<int:id>', methods=['GET', 'POST'])
def carrito(id):
    
    nombre_completo = request.form.get('nombre_completo', 'No especificado')
    email = request.form.get('email', 'No especificado')
    telefono = request.form.get('telefono', 'No especificado')
    documento = request.form.get('documento', 'No especificado')
    tipo_viaje = request.form.get('tipo_viaje', 'No especificado')
    fecha_salida = request.form.get('fecha_salida', 'No especificada')
    fecha_regreso = request.form.get('fecha_regreso', 'No especificada')
    adultos = request.form.get('adultos', '1')
    ninos = request.form.get('ninos', '0')
    clase = request.form.get('clase', 'No especificada')
    comentarios = request.form.get('comentarios', '')
    

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM productos WHERE idProducto=%s", (id,))
    producto = cursor.fetchone()
    cursor.close()

    if not producto:
        flash("Producto no encontrado", "error")
        return redirect(url_for('catalogo'))


    producto_con_detalles = {
        'id': producto['idProducto'],
        'nombre_producto': producto['nombre_producto'],
        'precio': producto['precio'],
        'descripcion': producto.get('descripcion', ''),
        'imagen': producto.get('imagen', ''),
        
        'detalles_viaje': {
            'nombre_completo': nombre_completo,
            'email': email,
            'telefono': telefono,
            'documento': documento,
            'tipo_viaje': tipo_viaje,
            'fecha_salida': fecha_salida,
            'fecha_regreso': fecha_regreso,
            'adultos': adultos,
            'ninos': ninos,
            'clase': clase,
            'comentarios': comentarios
        }
    }

    if "carrito" not in session:
        session['carrito'] = []

    session['carrito'].append(producto_con_detalles)
    session.modified = True
    flash(f"{producto['nombre_producto']} añadido al carrito", "success")

    return redirect(url_for('mostrar_carrito'))


@app.route('/mostrar_carrito')
def mostrar_carrito():
    carrito = session.get("carrito", [])
    
    
    carrito_filtrado = []
    total = 0
    
    for producto in carrito:
        if producto is not None and 'precio' in producto:
            try:
                
                precio = float(producto['precio'])
                total += precio
                carrito_filtrado.append(producto)
            except (ValueError, TypeError):
                
                continue
 
    session['carrito'] = carrito_filtrado
    session.modified = True
    
    return render_template("carrito.html", carrito=carrito_filtrado, total=total)
@app.route('/agregar_al_carrito_con_detalles/<int:id>', methods=['GET', 'POST'])
def agregar_al_carrito_con_detalles(id):
    if 'usuario' not in session:
        flash("Debes iniciar sesión para agregar productos al carrito.")
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM productos WHERE idProducto=%s", (id,))
    producto = cursor.fetchone()
    cursor.close()

    if not producto:
        flash("Producto no encontrado", "error")
        return redirect(url_for('catalogo'))

    if request.method == 'POST':
        # Validar que todos los campos obligatorios estén completos
        campos_obligatorios = [
            'nombre_completo', 'email', 'telefono', 'documento',
            'tipo_viaje', 'fecha_salida', 'fecha_regreso', 'adultos', 'clase'
        ]
        
        for campo in campos_obligatorios:
            if not request.form.get(campo):
                flash(f"El campo {campo.replace('_', ' ').title()} es obligatorio", "error")
                return render_template('detalles_viaje.html', producto=producto)

        # Capturar todos los datos del formulario
        nombre_completo = request.form['nombre_completo']
        email = request.form['email']
        telefono = request.form['telefono']
        documento = request.form['documento']
        tipo_viaje = request.form['tipo_viaje']
        fecha_salida = request.form['fecha_salida']
        fecha_regreso = request.form['fecha_regreso']
        adultos = request.form['adultos']
        ninos = request.form.get('ninos', '0')
        clase = request.form['clase']
        comentarios = request.form.get('comentarios', '')

        # Crear objeto de producto con toda la información del viaje
        producto_con_detalles = {
            'id': producto['idProducto'],
            'nombre_producto': producto['nombre_producto'],
            'precio': producto['precio'],
            'descripcion': producto.get('descripcion', ''),
            'imagen': producto.get('imagen', ''),
            'detalles_viaje': {
                'nombre_completo': nombre_completo,
                'email': email,
                'telefono': telefono,
                'documento': documento,
                'tipo_viaje': tipo_viaje,
                'fecha_salida': fecha_salida,
                'fecha_regreso': fecha_regreso,
                'adultos': adultos,
                'ninos': ninos,
                'clase': clase,
                'comentarios': comentarios
            }
        }

        if "carrito" not in session:
            session['carrito'] = []

        session['carrito'].append(producto_con_detalles)
        session.modified = True
        flash(f"✅ {producto['nombre_producto']} añadido al carrito con todos los detalles", "success")
        return redirect(url_for('mostrar_carrito'))

    
    return render_template('detalles_viaje.html', producto=producto)
    
@app.route('/factura')
def factura():
    carrito = session.get("carrito", [])
    metodo_pago = session.get('metodo_pago')
    
    if not carrito:
        flash("No hay productos en el carrito.")
        return redirect(url_for('catalogo'))
    
    if not metodo_pago:
        flash("No se ha seleccionado método de pago.")
        return redirect(url_for('mostrar_carrito'))
    
    total = 0
    carrito_valido = []
    
    for producto in carrito:
        if producto is not None and 'precio' in producto:
            try:
                precio = float(producto['precio'])
                total += precio
                carrito_valido.append(producto)
            except (ValueError, TypeError):
                continue
    
    numero_factura = f"{datetime.now().strftime('%Y%m%d')}{secrets.randbelow(10000):04d}"
    
    # CORRECCIÓN: Preparar datos para el email con información completa
    factura_data = {
        'numero_factura': numero_factura,
        'fecha': datetime.now().strftime('%Y-%m-%d'),
        'total': f"{(total * 1.1):.2f}",
        'metodo_pago': metodo_pago,
        'productos': []
    }
    
    for producto in carrito_valido:
        producto_info = {
            'nombre': producto['nombre_producto'],
            'precio': producto['precio']
        }
        
        # CORRECCIÓN: Asegurar que los detalles del viaje se incluyan correctamente
        if 'detalles_viaje' in producto and producto['detalles_viaje']:
            detalles = producto['detalles_viaje']
            producto_info['detalles_viaje'] = {
                'fecha_salida': detalles.get('fecha_salida', 'No especificada'),
                'fecha_regreso': detalles.get('fecha_regreso', 'No especificada'),
                'adultos': detalles.get('adultos', '1'),
                'ninos': detalles.get('ninos', '0'),
                'tipo_viaje': detalles.get('tipo_viaje', 'No especificado'),
                'clase': detalles.get('clase', 'No especificada'),
                'telefono': detalles.get('telefono', 'No especificado'),
                'email': detalles.get('email', 'No especificado'),
                'comentarios': detalles.get('comentarios', '')
            }
        else:
            # Si no hay detalles, agregar valores por defecto
            producto_info['detalles_viaje'] = {
                'fecha_salida': 'Por confirmar',
                'fecha_regreso': 'Por confirmar',
                'adultos': '1',
                'ninos': '0',
                'tipo_viaje': 'Estándar',
                'clase': 'Económica',
                'telefono': 'No especificado',
                'email': 'No especificado',
                'comentarios': ''
            }
        
        factura_data['productos'].append(producto_info)
    
    print(f"DEBUG - Datos para email: {factura_data}")
    
    if 'usuario' in session:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT username FROM usuarios WHERE idUsuario = %s", (session['idUsuario'],))
        usuario = cursor.fetchone()
        cursor.close()
        
        if usuario:
            email_usuario = usuario[0]
            if enviar_correo_factura(email_usuario, factura_data):
                flash("✅ Se ha enviado un email de confirmación a tu correo")
            else:
                flash("⚠️ La compra se completó pero no se pudo enviar el email de confirmación")
        else:
            flash("⚠️ No se pudo obtener la información del usuario para enviar el email")
    else:
        flash("ℹ️ Inicia sesión para recibir confirmaciones por email en futuras compras")
    
    session.pop("carrito", None)
    session.pop("metodo_pago", None)
    
    return render_template("factura.html", 
                         carrito=carrito_valido, 
                         total=total,
                         metodo_pago=metodo_pago,
                         numero_factura=numero_factura,
                         hoy=datetime.now().strftime('%Y-%m-%d'))

@app.route('/eliminar_del_carrito/<int:index>')
def eliminar_del_carrito(index):
    if 'carrito' in session and 0 <= index < len(session['carrito']):
        producto_eliminado = session['carrito'].pop(index)
        session.modified = True
        if producto_eliminado and 'nombre_producto' in producto_eliminado:
            flash(f"{producto_eliminado['nombre_producto']} eliminado del carrito", "info")
        else:
            flash("Producto eliminado del carrito", "info")
    
    return redirect(url_for('mostrar_carrito'))
 
@app.route('/reservas')
def reservas():
    if 'usuario' not in session:
        flash("Debes iniciar sesión para realizar reservas.")
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM productos WHERE cantidad > 0")
    productos = cursor.fetchall()
    cursor.close()
    
 
    hoy = datetime.now().strftime('%Y-%m-%d')
    
    return render_template("reservas.html", productos=productos, hoy=hoy)

 
@app.route('/procesar_reserva', methods=['POST'])
def procesar_reserva():
    try:
        nombre_completo = request.form['nombre_completo']
        email = request.form['email']
        telefono = request.form['telefono']
        documento = request.form['documento']
        id_producto = request.form['id_producto']
        tipo_viaje = request.form['tipo_viaje']
        fecha_salida = request.form['fecha_salida']
        fecha_regreso = request.form['fecha_regreso']
        adultos = request.form['adultos']
        ninos = request.form.get('ninos', 0)
        clase = request.form['clase']
        comentarios = request.form.get('comentarios', '')
        
        if not all([nombre_completo, email, telefono, documento, id_producto, tipo_viaje, fecha_salida, fecha_regreso, adultos]):
            flash("Por favor, completa todos los campos obligatorios.")
            return redirect(url_for('reservas'))
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT nombre_producto, precio FROM productos WHERE idProducto = %s", (id_producto,))
        producto = cursor.fetchone()
        
        if not producto:
            flash("Producto no encontrado.")
            cursor.close()
            return redirect(url_for('reservas'))
        
        cursor.execute("""
            INSERT INTO reservas_viajes (
                idUsuario, idProducto, nombre_completo, email, telefono, documento,
                tipo_viaje, fecha_salida, fecha_regreso, adultos, ninos, clase,
                comentarios, destino, precio_total, estado
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pendiente')
        """, (
            session.get('idUsuario'), id_producto, nombre_completo, email, telefono, documento,
            tipo_viaje, fecha_salida, fecha_regreso, adultos, ninos, clase,
            comentarios, producto['nombre_producto'], producto['precio']
        ))
        
        mysql.connection.commit()
    
        reserva_id = cursor.lastrowid
        
        cursor.close()
        
        reserva_data = {
            'id_reserva': reserva_id,
            'nombre_completo': nombre_completo,
            'destino': producto['nombre_producto'],
            'fecha_salida': fecha_salida,
            'fecha_regreso': fecha_regreso,
            'adultos': adultos,
            'ninos': ninos,
            'tipo_viaje': tipo_viaje,
            'clase': clase,
            'precio_total': producto['precio'],
            'telefono': telefono
        }
        
        if enviar_correo_reserva(email, reserva_data):
            flash("✅ ¡Reserva realizada exitosamente! Se ha enviado un email de confirmación.")
        else:
            flash("⚠️ ¡Reserva realizada! Pero no se pudo enviar el email de confirmación.")
        
        reserva = {
            'idReserva': reserva_id,
            'nombre_completo': nombre_completo,
            'email': email,
            'telefono': telefono,
            'destino': producto['nombre_producto'],
            'tipo_viaje': tipo_viaje,
            'fecha_salida': fecha_salida,
            'fecha_regreso': fecha_regreso,
            'adultos': adultos,
            'ninos': ninos
        }
        
        return render_template("confirmacion_reserva.html", reserva=reserva)
        
    except Exception as e:
        error_msg = f"Error al procesar la reserva: {str(e)}"
        print(f"ERROR DETALLADO: {error_msg}")
        flash(error_msg)
        return redirect(url_for('reservas'))

@app.route('/procesar_pago', methods=['POST'])
def procesar_pago():
    if 'usuario' not in session:
        flash("Debes iniciar sesión para realizar pagos.")
        return redirect(url_for('login'))
    
    carrito = session.get("carrito", [])
    if not carrito:
        flash("Tu carrito está vacío.")
        return redirect(url_for('catalogo'))
    
    metodo_pago = request.form.get('metodo_pago')
    terms = request.form.get('terms')
    if not metodo_pago:
        flash("Por favor selecciona un método de pago.")
        return redirect(url_for('mostrar_carrito'))
    
    if not terms:
        flash("Debes aceptar los términos y condiciones.")
        return redirect(url_for('mostrar_carrito'))
    
    session['metodo_pago'] = metodo_pago
    
    print(f"DEBUG - Método de pago guardado: {session.get('metodo_pago')}")
    print(f"DEBUG - Usuario logueado: {session.get('usuario')}")
    print(f"DEBUG - ID Usuario: {session.get('idUsuario')}")
    
    return redirect(url_for('factura'))

if __name__ =='__main__':
    app.run(port=5000,debug=True)
    
